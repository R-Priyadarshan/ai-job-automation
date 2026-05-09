"""
============================================================
src/ai_engine/ats_matcher.py
------------------------------------------------------------
PURPOSE:
    Uses local AI (Ollama) to analyze how well a resume
    matches a job description and calculate an ATS score.

WHAT IS ATS?
    ATS = Applicant Tracking System
    Companies use ATS software to automatically filter resumes
    before a human ever reads them.

    ATS systems scan resumes for:
    - Exact keyword matches
    - Required skills
    - Job title relevance
    - Education requirements

    If your resume doesn't match, it gets rejected automatically!

HOW THIS WORKS:
    1. Take the job description text
    2. Take your resume text
    3. Send both to Ollama with a detailed analysis prompt
    4. AI returns: score, matching skills, missing skills, advice
    5. Also run TF-IDF semantic similarity as backup scoring

OUTPUT:
    {
        'score': 78,
        'matching_skills': ['Python', 'Machine Learning', 'Docker'],
        'missing_skills': ['Kubernetes', 'Go'],
        'analysis': 'Detailed AI analysis...',
        'suggestions': ['Add Kubernetes experience...'],
    }
============================================================
"""

import re                            # Regex for text processing
from loguru import logger            # Logging
from .ollama_client import OllamaClient
from .resume_parser import ResumeParser


class ATSMatcher:
    """
    Uses AI to match resumes against job descriptions
    and calculate ATS compatibility scores.
    """

    def __init__(self, config: dict):
        """
        Initialize ATS Matcher.

        Args:
            config: Config dict from config.yaml
        """
        self.config = config
        self.ai = OllamaClient(config)         # Our local AI client
        self.parser = ResumeParser()           # Resume text extractor

        # ATS thresholds from config
        ats_cfg = config.get('ats', {})
        self.min_score = ats_cfg.get('minimum_score', 60)

    def analyze(self, job: dict, resume_data: dict) -> dict:
        """
        Full ATS analysis — combines AI analysis with skill matching.

        Args:
            job: Job dict from database (title, company, description, skills)
            resume_data: Parsed resume dict from ResumeParser.parse()

        Returns:
            ATS analysis result dict with score, skills, suggestions.
        """
        logger.info(f"Analyzing ATS match: {job.get('title')} @ {job.get('company')}")

        # Get the texts we need
        job_description = job.get('description', '')
        job_skills_text = job.get('skills', '')
        resume_text = resume_data.get('full_text', '')
        resume_skills = resume_data.get('skills', [])

        # Combine job description and skills for analysis
        full_job_text = f"{job.get('title', '')} {job_description} {job_skills_text}"

        # METHOD 1: AI-based analysis (primary method)
        ai_result = self._ai_ats_analysis(
            job_title=job.get('title', ''),
            company=job.get('company', ''),
            job_text=full_job_text,
            resume_text=resume_text[:3000],  # Limit to 3000 chars for AI
            resume_skills=resume_skills,
        )

        # METHOD 2: Skill-based matching (fast backup)
        skill_result = self._skill_based_matching(
            job_text=full_job_text,
            resume_skills=resume_skills,
        )

        # Combine both results
        # If AI gives a valid score, use it; otherwise use skill matching
        if ai_result.get('score', 0) > 0:
            # Blend AI score (70%) with skill score (30%)
            final_score = int(
                0.7 * ai_result.get('score', 0) +
                0.3 * skill_result.get('score', 0)
            )
        else:
            final_score = skill_result.get('score', 0)

        # Build final result
        result = {
            'job_id':           job.get('id'),
            'score':            min(100, max(0, final_score)),  # Clamp 0-100
            'matching_skills':  skill_result.get('matching', []),
            'missing_skills':   skill_result.get('missing', []),
            'analysis_text':    ai_result.get('analysis', ''),
            'suggestions':      ai_result.get('suggestions', []),
            'meets_threshold':  final_score >= self.min_score,
        }

        logger.info(f"ATS Score: {result['score']}/100")
        return result

    def _ai_ats_analysis(
        self,
        job_title: str,
        company: str,
        job_text: str,
        resume_text: str,
        resume_skills: list
    ) -> dict:
        """
        Uses Ollama AI to perform deep ATS analysis.

        The AI acts as an ATS expert and analyzes the resume
        against the job description holistically.

        Args:
            job_title: Title of the job position.
            company: Company name.
            job_text: Full job description + skills text.
            resume_text: Full resume text (truncated).
            resume_skills: List of skills extracted from resume.

        Returns:
            Dict with AI analysis results.
        """
        # Format the skills list for the prompt
        resume_skills_str = ', '.join(resume_skills) if resume_skills else 'Not extracted'

        # This is the main ATS analysis prompt
        # Carefully crafted to get structured, useful output
        prompt = f"""
You are an expert ATS (Applicant Tracking System) analyst and career coach.

Analyze how well this resume matches the job description below.

=== JOB DETAILS ===
Job Title: {job_title}
Company: {company}

Job Description:
{job_text[:2000]}

=== CANDIDATE RESUME ===
Detected Skills: {resume_skills_str}

Resume Text:
{resume_text[:2000]}

=== YOUR TASK ===
Analyze the match and provide:

1. ATS_SCORE: Give an integer score from 0-100
   - 90-100: Perfect match
   - 70-89: Strong match, apply immediately
   - 50-69: Good match, some skill gaps
   - 30-49: Weak match, significant gaps
   - 0-29: Poor match, major missing requirements

2. MATCHING_SKILLS: List skills found in BOTH the resume AND job description

3. MISSING_SKILLS: List skills required by the job but NOT found in resume

4. ANALYSIS: 2-3 sentences explaining the overall match

5. SUGGESTIONS: 3-5 specific improvements to increase ATS score

Respond in this EXACT format:
ATS_SCORE: [number]
MATCHING_SKILLS: [skill1, skill2, skill3]
MISSING_SKILLS: [skill1, skill2]
ANALYSIS: [your analysis here]
SUGGESTIONS:
- [suggestion 1]
- [suggestion 2]
- [suggestion 3]
"""

        system_prompt = (
            "You are an expert ATS systems analyst. "
            "Be precise, honest, and specific. "
            "Never inflate scores. Give realistic assessments."
        )

        # Get AI response
        response = self.ai.generate(prompt, system_prompt)

        # Parse the structured response
        return self._parse_ai_response(response)

    def _parse_ai_response(self, response: str) -> dict:
        """
        Parses the structured AI response into a Python dictionary.

        Args:
            response: Raw text response from AI.

        Returns:
            Dict with parsed score, skills, analysis, suggestions.
        """
        result = {
            'score': 0,
            'matching': [],
            'missing': [],
            'analysis': response,  # Keep full response as fallback
            'suggestions': [],
        }

        if not response or response.startswith('ERROR'):
            return result

        lines = response.split('\n')

        # Parse line by line using prefix matching
        in_suggestions = False
        suggestions = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # ATS Score line: "ATS_SCORE: 75"
            if line.startswith('ATS_SCORE:'):
                try:
                    score_text = line.replace('ATS_SCORE:', '').strip()
                    # Extract number even if AI adds extra text
                    score_match = re.search(r'\d+', score_text)
                    if score_match:
                        result['score'] = int(score_match.group())
                except (ValueError, AttributeError):
                    pass

            # Matching skills: "MATCHING_SKILLS: Python, TensorFlow, Docker"
            elif line.startswith('MATCHING_SKILLS:'):
                skills_text = line.replace('MATCHING_SKILLS:', '').strip()
                skills_text = skills_text.strip('[]')  # Remove brackets
                result['matching'] = [
                    s.strip() for s in skills_text.split(',')
                    if s.strip() and s.strip().lower() not in ['none', 'n/a']
                ]

            # Missing skills: "MISSING_SKILLS: Kubernetes, Go"
            elif line.startswith('MISSING_SKILLS:'):
                skills_text = line.replace('MISSING_SKILLS:', '').strip()
                skills_text = skills_text.strip('[]')
                result['missing'] = [
                    s.strip() for s in skills_text.split(',')
                    if s.strip() and s.strip().lower() not in ['none', 'n/a']
                ]

            # Analysis paragraph
            elif line.startswith('ANALYSIS:'):
                result['analysis'] = line.replace('ANALYSIS:', '').strip()

            # Suggestions section header
            elif line.startswith('SUGGESTIONS:'):
                in_suggestions = True

            # Suggestion bullets: "- Add Kubernetes experience"
            elif in_suggestions and line.startswith('-'):
                suggestions.append(line.lstrip('- ').strip())

        result['suggestions'] = suggestions
        return result

    def _skill_based_matching(self, job_text: str, resume_skills: list) -> dict:
        """
        Fast skill-based matching using keyword comparison.
        Used as a backup/validation alongside AI scoring.

        Args:
            job_text: Job description + skills text.
            resume_skills: Skills extracted from resume.

        Returns:
            Dict with score, matching skills, missing skills.
        """
        if not resume_skills:
            return {'score': 0, 'matching': [], 'missing': []}

        job_text_lower = job_text.lower()

        # Find which resume skills appear in the job description
        matching = []
        for skill in resume_skills:
            if skill.lower() in job_text_lower:
                matching.append(skill)

        # Find skills mentioned in job but not in resume
        # Use our standard skill list from ResumeParser
        parser = ResumeParser()
        all_skills = parser.tech_skills

        missing = []
        for skill in all_skills:
            if skill.lower() in job_text_lower and skill not in resume_skills:
                missing.append(skill)

        # Calculate score
        # Score = (matching skills / required skills) * 100
        # With a cap at 100
        total_required = len(matching) + len(missing)
        if total_required == 0:
            score = 50  # If no skills detected, give neutral score
        else:
            score = int((len(matching) / total_required) * 100)

        return {
            'score': min(100, score),
            'matching': matching,
            'missing': missing[:10],  # Limit missing list
        }

    def get_score_color(self, score: int) -> str:
        """
        Returns a color string based on the ATS score.
        Used for dashboard visualization.

        Args:
            score: ATS score 0-100.

        Returns:
            Color string (green/yellow/orange/red).
        """
        if score >= 80:
            return 'green'
        elif score >= 60:
            return 'yellow'
        elif score >= 40:
            return 'orange'
        else:
            return 'red'

    def get_score_label(self, score: int) -> str:
        """
        Returns a text label for the ATS score.

        Args:
            score: ATS score 0-100.

        Returns:
            Human-readable label.
        """
        if score >= 85:
            return "🟢 Excellent Match — Apply Now!"
        elif score >= 70:
            return "🟡 Good Match — Apply"
        elif score >= 55:
            return "🟠 Fair Match — Optimize Resume First"
        elif score >= 40:
            return "🔴 Weak Match — Significant Gaps"
        else:
            return "⛔ Poor Match — Not Recommended"
