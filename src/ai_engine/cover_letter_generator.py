"""
============================================================
src/ai_engine/cover_letter_generator.py
------------------------------------------------------------
PURPOSE:
    Generates personalized cover letters for each job using
    the local AI model through Ollama.

WHAT MAKES A GOOD COVER LETTER:
    1. Personalized — mentions company name and specific role
    2. Shows knowledge — references company's work/mission
    3. Highlights matching skills — directly relevant to job
    4. Shows enthusiasm — genuine interest in the position
    5. Professional tone — formal but not robotic
    6. Concise — typically 300-400 words, 3-4 paragraphs

HOW IT WORKS:
    1. Gather: job details + resume data + ATS matching results
    2. Build a detailed AI prompt with all this context
    3. Ollama generates a personalized cover letter
    4. Format and clean the output
    5. Return as text (then saved to PDF)

ALSO GENERATES:
    - Recruiter email drafts (shorter, for cold outreach)
============================================================
"""

from loguru import logger
from .ollama_client import OllamaClient
from datetime import date


class CoverLetterGenerator:
    """
    Generates personalized cover letters and recruiter emails
    using local AI through Ollama.
    """

    def __init__(self, config: dict):
        """
        Initialize with config.

        Args:
            config: Config dict from config.yaml
        """
        self.config = config
        self.ai = OllamaClient(config)
        self.user_config = config.get('user', {})

    def generate_cover_letter(
        self,
        job: dict,
        resume_data: dict,
        ats_result: dict
    ) -> str:
        """
        Generates a personalized cover letter for a specific job.

        Args:
            job: Job dict from database.
            resume_data: Parsed resume from ResumeParser.
            ats_result: ATS analysis result from ATSMatcher.

        Returns:
            Cover letter as plain text string (Markdown formatted).
        """
        logger.info(f"Generating cover letter for: {job.get('title')} @ {job.get('company')}")

        user = self.user_config
        matching_skills = ats_result.get('matching_skills', [])
        today = date.today().strftime('%B %d, %Y')  # e.g., "January 15, 2025"

        # Get top matching skills to highlight (max 5)
        top_skills = matching_skills[:5]
        skills_highlight = ', '.join(top_skills) if top_skills else 'relevant technical skills'

        # Get experience summary
        experience = resume_data.get('experience', [])
        experience_preview = experience[:3] if experience else []
        experience_str = '\n'.join(f"- {e}" for e in experience_preview)

        prompt = f"""
You are an expert cover letter writer. Write a compelling, personalized cover letter.

=== JOB DETAILS ===
Job Title: {job.get('title', '')}
Company: {job.get('company', '')}
Location: {job.get('location', 'Remote')}
Job URL: {job.get('url', '')}

Job Description (excerpt):
{job.get('description', '')[:1000]}

=== CANDIDATE INFO ===
Name: {user.get('name', 'Your Name')}
Email: {user.get('email', 'your@email.com')}
Phone: {user.get('phone', '+91-XXXXXXXXXX')}
LinkedIn: {user.get('linkedin', 'linkedin.com/in/yourprofile')}
Location: {user.get('location', 'India')}

Top Matching Skills: {skills_highlight}

Relevant Experience:
{experience_str if experience_str else "Strong technical background in AI/ML and software development"}

=== WRITING GUIDELINES ===
Write a 3-4 paragraph cover letter that:

1. OPENING PARAGRAPH:
   - Start with genuine enthusiasm for THIS specific company
   - Mention the exact job title
   - Give one powerful hook statement

2. SKILLS PARAGRAPH:
   - Highlight 2-3 most relevant skills for this role
   - Connect each skill to a specific achievement or project
   - Use metrics where possible (% improvement, scale, etc.)

3. COMPANY FIT PARAGRAPH:
   - Show you understand the company's work/mission
   - Explain why you specifically want to work there
   - Connect your goals to theirs

4. CLOSING PARAGRAPH:
   - Express enthusiasm for next steps
   - Professional call to action
   - Thank them for their time

=== FORMAT ===
Date: {today}

[Hiring Manager]
{job.get('company', 'Company Name')}

Dear Hiring Manager,

[Write 3-4 engaging paragraphs here]

Sincerely,
{user.get('name', 'Your Name')}
{user.get('email', 'your@email.com')}
{user.get('phone', '+91-XXXXXXXXXX')}
{user.get('linkedin', 'linkedin.com/in/yourprofile')}

Write the complete cover letter now. Be specific, authentic, and compelling.
Do NOT use generic phrases like "I am writing to express my interest."
Start with something impactful and unique.
"""

        system_prompt = (
            "You are a world-class cover letter writer and career coach. "
            "You write cover letters that get interviews. "
            "You are specific, authentic, and compelling. "
            "You never use clichés. Every letter feels genuinely personal. "
            "You are HONEST — never claim skills the candidate doesn't have."
        )

        cover_letter = self.ai.generate(prompt, system_prompt)

        if cover_letter.startswith('ERROR'):
            logger.error("AI failed to generate cover letter")
            return self._fallback_cover_letter(job, user, skills_highlight, today)

        logger.info(f"Cover letter generated: {len(cover_letter)} characters")
        return cover_letter

    def generate_recruiter_email(self, job: dict, resume_data: dict) -> str:
        """
        Generates a short cold outreach email to send to a recruiter.
        This is for proactive outreach, not a job application response.

        Args:
            job: Job dict from database.
            resume_data: Parsed resume dict.

        Returns:
            Email draft as plain text string.
        """
        user = self.user_config
        skills = resume_data.get('skills', [])
        top_skills = ', '.join(skills[:4]) if skills else 'Python, Machine Learning'

        prompt = f"""
Write a SHORT, professional cold email to a recruiter at {job.get('company', 'the company')}.

Context:
- Job Applied For: {job.get('title', '')}
- My Top Skills: {top_skills}
- My Name: {user.get('name', 'Your Name')}
- LinkedIn: {user.get('linkedin', '')}

Requirements:
- Maximum 150 words
- Subject line included
- Mention the specific job title
- One specific technical achievement
- Clear call to action
- Professional but personable tone
- NO generic phrases

Format:
Subject: [Compelling subject line]

Hi [Recruiter Name / Hiring Team],

[Email body]

Best regards,
{user.get('name', 'Your Name')}
{user.get('linkedin', '')}
{user.get('email', '')}

Write the complete email now.
"""

        email = self.ai.generate(prompt)

        if email.startswith('ERROR'):
            return self._fallback_email(job, user, top_skills)

        return email

    def _fallback_cover_letter(
        self, job: dict, user: dict, skills: str, today: str
    ) -> str:
        """
        Fallback cover letter when AI is unavailable.

        Args:
            job: Job dict.
            user: User config dict.
            skills: Skills string.
            today: Today's date string.

        Returns:
            Basic cover letter string.
        """
        return f"""{today}

Hiring Manager
{job.get('company', 'Company')}

Dear Hiring Manager,

I am excited to apply for the {job.get('title', 'position')} role at {job.get('company', 'your company')}. With strong expertise in {skills}, I am confident I can make a significant contribution to your team.

My background in software development and AI/ML has equipped me with the technical skills directly relevant to this role. I am passionate about solving complex problems and delivering high-quality solutions.

I am particularly excited about the opportunity at {job.get('company', 'your company')} because of its innovative work in the field. I would love to bring my skills and enthusiasm to your team and grow together.

I look forward to discussing how I can contribute to {job.get('company', 'your company')}'s success. Please find my resume attached. Thank you for your consideration.

Sincerely,
{user.get('name', 'Your Name')}
{user.get('email', 'your@email.com')}
{user.get('phone', '+91-XXXXXXXXXX')}
{user.get('linkedin', 'linkedin.com/in/yourprofile')}
"""

    def _fallback_email(self, job: dict, user: dict, skills: str) -> str:
        """Fallback recruiter email when AI is unavailable."""
        return f"""Subject: Application for {job.get('title', 'Position')} — {user.get('name', 'Your Name')}

Hi Hiring Team,

I came across the {job.get('title', 'position')} opening at {job.get('company', 'your company')} and I am very interested.

I have strong experience in {skills} and would love to contribute to your team. My profile: {user.get('linkedin', '')}

Would love to connect — available for a quick call this week.

Best regards,
{user.get('name', 'Your Name')}
{user.get('email', '')}
"""
