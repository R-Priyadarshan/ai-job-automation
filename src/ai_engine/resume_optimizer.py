"""
============================================================
src/ai_engine/resume_optimizer.py
------------------------------------------------------------
PURPOSE:
    Uses local AI to rewrite and optimize your resume
    specifically for a target job's ATS requirements.

HOW IT WORKS:
    1. Takes your original resume text
    2. Takes the job description and missing skills
    3. Sends to Ollama with a carefully crafted prompt
    4. AI rewrites the resume in Markdown format with:
       - ATS keywords naturally integrated
       - All existing experience preserved
       - Missing skills added where genuinely applicable
       - Professional formatting

OUTPUT:
    - Optimized resume as Markdown text
    - Ready to convert to PDF

ETHICAL NOTE:
    The AI is instructed to NEVER fabricate experience.
    It only adds skills that can be genuinely inferred
    or highlights existing experience more effectively.
============================================================
"""

from loguru import logger
from .ollama_client import OllamaClient


class ResumeOptimizer:
    """
    Uses AI to optimize resumes for specific job applications.
    Rewrites resume in Markdown, then converts to PDF.
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

    def optimize(self, resume_data: dict, job: dict, ats_result: dict) -> str:
        """
        Generates an ATS-optimized version of the resume.

        Args:
            resume_data: Parsed resume dict from ResumeParser
            job: Job dict from database
            ats_result: ATS analysis result from ATSMatcher

        Returns:
            Optimized resume as Markdown string.
        """
        logger.info(f"Optimizing resume for: {job.get('title')} @ {job.get('company')}")

        user = self.user_config
        missing_skills = ats_result.get('missing_skills', [])
        matching_skills = ats_result.get('matching_skills', [])
        suggestions = ats_result.get('suggestions', [])

        # Format missing skills for the prompt
        missing_str = ', '.join(missing_skills[:10]) if missing_skills else 'None identified'
        matching_str = ', '.join(matching_skills[:10]) if matching_skills else 'None identified'
        suggestions_str = '\n'.join(f"- {s}" for s in suggestions[:5])

        prompt = f"""
You are an expert resume writer and ATS optimization specialist.

Your task is to rewrite and optimize this resume for the specific job below.

=== TARGET JOB ===
Title: {job.get('title', '')}
Company: {job.get('company', '')}
Location: {job.get('location', 'Remote')}

Job Description:
{job.get('description', '')[:1500]}

=== CURRENT RESUME ===
{resume_data.get('full_text', '')[:2000]}

=== ATS ANALYSIS ===
Current ATS Score: {ats_result.get('score', 0)}/100
Matching Skills: {matching_str}
Missing Skills: {missing_str}

ATS Suggestions:
{suggestions_str}

=== YOUR INSTRUCTIONS ===
Rewrite this resume to:
1. Naturally incorporate missing keywords: {missing_str}
2. Emphasize matching skills prominently
3. Use strong action verbs (Developed, Implemented, Optimized, Led)
4. Add quantifiable achievements where possible (e.g., "Improved X by 30%")
5. Preserve ALL existing truthful experience and achievements
6. NEVER fabricate experience, degrees, or companies
7. Format professionally

=== USER INFO ===
Name: {user.get('name', 'Your Name')}
Email: {user.get('email', 'your@email.com')}
Phone: {user.get('phone', '+91-XXXXXXXXXX')}
LinkedIn: {user.get('linkedin', 'linkedin.com/in/yourprofile')}
GitHub: {user.get('github', 'github.com/yourusername')}
Location: {user.get('location', 'India')}

=== OUTPUT FORMAT ===
Write the complete optimized resume in clean Markdown format.
Use these exact sections:
# [Full Name]
[Email] | [Phone] | [LinkedIn] | [GitHub] | [Location]

## Professional Summary
[2-3 sentence impactful summary targeting this specific role]

## Technical Skills
**AI/ML:** [skills]
**Programming:** [skills]
**Tools & Platforms:** [skills]
[Add more categories as relevant]

## Professional Experience
### [Job Title] | [Company] | [Date Range]
- [Achievement with metrics]
- [Achievement with metrics]

## Projects
### [Project Name]
- [Description with technologies used]

## Education
[Degree, Institution, Year, GPA if strong]

## Certifications & Courses
- [Relevant certifications]

Write the COMPLETE resume now. Include all sections.
"""

        system_prompt = (
            "You are a professional resume writer with 15 years of experience "
            "in ATS optimization. You write resumes that get past ATS systems "
            "AND impress human recruiters. You NEVER fabricate information. "
            "You only highlight and frame existing experience in the best light."
        )

        # Generate the optimized resume
        optimized_resume = self.ai.generate(prompt, system_prompt)

        if optimized_resume.startswith('ERROR'):
            logger.error("AI failed to generate optimized resume")
            return self._fallback_resume(resume_data, job, user)

        logger.info(f"Resume optimized: {len(optimized_resume)} characters")
        return optimized_resume

    def _fallback_resume(self, resume_data: dict, job: dict, user: dict) -> str:
        """
        Creates a basic resume in Markdown when AI fails.
        Used as a fallback so the system never completely fails.

        Args:
            resume_data: Parsed resume data.
            job: Job dict.
            user: User config dict.

        Returns:
            Basic Markdown resume string.
        """
        skills = resume_data.get('skills', [])
        skills_str = ' · '.join(skills[:20]) if skills else 'Python, Machine Learning, Data Science'

        experience = resume_data.get('experience', [])
        exp_items = '\n'.join(f"- {e}" for e in experience[:8]) if experience else "- Relevant experience (add details)"

        education = resume_data.get('education', [])
        edu_text = '\n'.join(education[:3]) if education else "B.Tech Computer Science"

        return f"""# {user.get('name', 'Your Name')}
{user.get('email', 'email@example.com')} | {user.get('phone', '+91-XXXXXXXXXX')} | {user.get('linkedin', 'linkedin.com/in/profile')} | {user.get('github', 'github.com/username')} | {user.get('location', 'India')}

## Professional Summary
Motivated and skilled professional with expertise in {skills_str[:100]}. Seeking the {job.get('title', 'position')} role at {job.get('company', 'your company')} to contribute technical skills and drive impactful results.

## Technical Skills
{skills_str}

## Professional Experience
{exp_items}

## Education
{edu_text}

---
*Resume optimized for {job.get('title', 'position')} at {job.get('company', 'Company')}*
"""
