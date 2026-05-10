"""
============================================================
src/ai_engine/cold_mail_generator.py
------------------------------------------------------------
PURPOSE:
    Generates personalised cold emails for internship outreach.
    Uses local Ollama AI to craft emails that:
    - Are specific to the company and role
    - Highlight the candidate's most relevant skills
    - Ask specifically for an INTERNSHIP opportunity
    - Are short, punchy, and professional (under 200 words)
    - Include a clear call to action

DIFFERENCE FROM COVER LETTER:
    Cover letter  → formal, long, for job applications
    Cold email    → short, direct, for internship outreach
                    sent even when no opening is listed

WHAT GETS GENERATED:
    1. Subject line  — compelling, specific, not spammy
    2. Email body    — 3 short paragraphs, under 200 words
    3. Recruiter email — extracted from job listing if available
============================================================
"""

from loguru import logger
from .ollama_client import OllamaClient


class ColdMailGenerator:
    """
    Generates personalised cold internship outreach emails
    using local Ollama AI.
    """

    def __init__(self, config: dict):
        """
        Initialize with config.

        Args:
            config: Config dict from config.yaml
        """
        self.config = config
        self.ai = OllamaClient(config)
        self.user = config.get('user', {})

    def generate_cold_email(
        self,
        job: dict,
        resume_data: dict,
        ats_result: dict,
    ) -> dict:
        """
        Generates a complete cold internship email for a job listing.

        Args:
            job:         Job dict from database.
            resume_data: Parsed resume from ResumeParser.
            ats_result:  ATS analysis result from ATSMatcher.

        Returns:
            dict with keys:
                'subject'    — email subject line
                'body'       — full email body text
                'to_email'   — recruiter email if found, else None
        """
        logger.info(
            f"Generating cold email for: "
            f"{job.get('title')} @ {job.get('company')}"
        )

        matching_skills = ats_result.get('matching_skills', [])
        top_skills = ', '.join(matching_skills[:4]) if matching_skills else \
                     ', '.join(resume_data.get('skills', [])[:4])

        # Pull experience highlights
        experience = resume_data.get('experience', [])
        best_exp = experience[0] if experience else "strong technical projects"

        prompt = f"""
You are writing a cold internship outreach email on behalf of a student/fresher.

=== TARGET JOB ===
Company: {job.get('company', 'the company')}
Role: {job.get('title', 'Software Engineer')}
Location: {job.get('location', 'Remote')}

=== CANDIDATE ===
Name: {self.user.get('name', 'Candidate')}
Email: {self.user.get('email', '')}
LinkedIn: {self.user.get('linkedin', '')}
GitHub: {self.user.get('github', '')}
Location: {self.user.get('location', 'India')}
Top Skills: {top_skills}
Best Experience: {best_exp}

=== TASK ===
Write a cold email asking for an INTERNSHIP opportunity at {job.get('company')}.

STRICT RULES:
- Maximum 180 words in the body
- 3 short paragraphs only
- Paragraph 1: Who you are + one impressive hook (1-2 sentences)
- Paragraph 2: Why THIS company specifically + your top 2 relevant skills (2-3 sentences)
- Paragraph 3: Clear ask for internship + call to action (1-2 sentences)
- DO NOT use: "I hope this email finds you well", "I am writing to express", "passionate about"
- DO use: specific company name, specific skills, specific ask
- Tone: confident, direct, professional but human
- End with full signature

OUTPUT FORMAT (exactly):
SUBJECT: [subject line here]

Hi [Hiring Manager / Team],

[Paragraph 1]

[Paragraph 2]

[Paragraph 3]

Best regards,
{self.user.get('name', 'Your Name')}
{self.user.get('email', '')}
{self.user.get('linkedin', '')}
{self.user.get('github', '')}

Write the email now. Be specific and compelling.
"""

        system_prompt = (
            "You are an expert at writing cold outreach emails that get responses. "
            "You write short, specific, confident emails. "
            "You never use clichés. You always mention the company by name. "
            "You write as if you genuinely want THIS specific internship."
        )

        result = self.ai.generate(prompt, system_prompt)

        if result.startswith('ERROR'):
            logger.warning("AI unavailable — using fallback cold email")
            return self._fallback_cold_email(job, top_skills)

        # Parse subject and body from AI output
        subject, body = self._parse_email_output(result, job)

        # Try to extract recruiter email from job description
        to_email = self._extract_recruiter_email(job)

        logger.info(f"Cold email generated ({len(body)} chars)")

        return {
            'subject':  subject,
            'body':     body,
            'to_email': to_email,
        }

    def generate_followup_email(self, job: dict, days_since: int = 7) -> dict:
        """
        Generates a polite follow-up email for a job already applied to.

        Args:
            job:         Job dict from database.
            days_since:  Days since the original application.

        Returns:
            dict with 'subject' and 'body'.
        """
        prompt = f"""
Write a short, polite follow-up email for an internship application.

Company: {job.get('company')}
Role: {job.get('title')}
Days since application: {days_since}
My name: {self.user.get('name')}

Rules:
- Under 80 words
- Polite, not pushy
- Restate interest briefly
- Ask for update on timeline
- Include name and LinkedIn

OUTPUT FORMAT:
SUBJECT: [subject]

[body]

Best,
{self.user.get('name')}
{self.user.get('linkedin', '')}
"""
        result = self.ai.generate(prompt)

        if result.startswith('ERROR'):
            return {
                'subject': f"Following up: {job.get('title')} Internship Application",
                'body': (
                    f"Hi,\n\nI wanted to follow up on my internship application "
                    f"for the {job.get('title')} role at {job.get('company')} "
                    f"from {days_since} days ago.\n\n"
                    f"I remain very interested and would love to hear about "
                    f"the next steps.\n\n"
                    f"Best regards,\n{self.user.get('name')}\n"
                    f"{self.user.get('linkedin', '')}"
                )
            }

        subject, body = self._parse_email_output(result, job)
        return {'subject': subject, 'body': body}

    def _parse_email_output(self, ai_output: str, job: dict) -> tuple:
        """
        Parses AI output into subject and body.

        Args:
            ai_output: Raw AI-generated text.
            job:       Job dict for fallback subject.

        Returns:
            Tuple of (subject, body).
        """
        lines = ai_output.strip().split('\n')
        subject = f"Internship Application — {job.get('title')} @ {job.get('company')}"
        body_lines = []
        found_subject = False

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Extract subject line
            if stripped.upper().startswith('SUBJECT:'):
                subject = stripped[8:].strip()
                found_subject = True
                continue

            # Everything after subject is body
            if found_subject:
                body_lines.append(line)

        # If no SUBJECT: marker found, use all as body
        if not found_subject:
            body_lines = lines

        body = '\n'.join(body_lines).strip()

        # Clean up any leftover markers
        body = body.replace('SUBJECT:', '').strip()

        return subject, body

    def _extract_recruiter_email(self, job: dict) -> str | None:
        """
        Tries to extract a recruiter/HR email from the job description.

        Args:
            job: Job dict.

        Returns:
            Email address string if found, None otherwise.
        """
        import re
        description = job.get('description', '') or ''
        # Simple email regex
        emails = re.findall(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            description
        )
        # Filter out common non-recruiter emails
        skip = {'example.com', 'test.com', 'noreply', 'no-reply'}
        for email in emails:
            if not any(s in email.lower() for s in skip):
                logger.debug(f"Found recruiter email in job description: {email}")
                return email
        return None

    def _fallback_cold_email(self, job: dict, skills: str) -> dict:
        """Fallback cold email when AI is unavailable."""
        subject = (
            f"Internship Application — {job.get('title')} | "
            f"{self.user.get('name')}"
        )
        body = (
            f"Hi Hiring Team,\n\n"
            f"I'm {self.user.get('name')}, a developer with strong skills in "
            f"{skills}. I came across {job.get('company')}'s work and I'm "
            f"genuinely excited about what you're building.\n\n"
            f"I'd love to contribute as an intern on your {job.get('title')} "
            f"team. I bring hands-on experience in {skills} and a strong "
            f"drive to learn and ship real work.\n\n"
            f"Would you be open to a 15-minute call this week? "
            f"My resume is attached.\n\n"
            f"Best regards,\n"
            f"{self.user.get('name')}\n"
            f"{self.user.get('email', '')}\n"
            f"{self.user.get('linkedin', '')}\n"
            f"{self.user.get('github', '')}"
        )
        return {'subject': subject, 'body': body, 'to_email': None}
