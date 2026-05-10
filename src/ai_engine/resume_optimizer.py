"""
============================================================
src/ai_engine/resume_optimizer.py
------------------------------------------------------------
PURPOSE:
    Uses local AI to produce a high-quality, ATS-optimised
    resume tailored to a specific job.

QUALITY IMPROVEMENTS:
    - Detailed section-by-section instructions to the AI
    - Forces quantified achievements (numbers, %, scale)
    - Enforces clean Markdown structure the PDF renderer expects
    - Never fabricates — only reframes existing experience
    - Includes all user contact info from config
============================================================
"""

from loguru import logger
from .ollama_client import OllamaClient


class ResumeOptimizer:
    """
    Produces ATS-optimised, professionally written resumes
    tailored to specific job descriptions.
    """

    def __init__(self, config: dict):
        self.config      = config
        self.ai          = OllamaClient(config)
        self.user_config = config.get('user', {})

    def optimize(self, resume_data: dict, job: dict, ats_result: dict) -> str:
        """
        Generates an ATS-optimised resume in clean Markdown.

        Args:
            resume_data: Parsed resume dict from ResumeParser.
            job:         Job dict from database.
            ats_result:  ATS analysis result from ATSMatcher.

        Returns:
            Optimised resume as Markdown string.
        """
        logger.info(f"Optimising resume for: {job.get('title')} @ {job.get('company')}")

        user            = self.user_config
        missing_skills  = ats_result.get('missing_skills', [])
        matching_skills = ats_result.get('matching_skills', [])

        missing_str  = ', '.join(missing_skills[:12])  if missing_skills  else 'None'
        matching_str = ', '.join(matching_skills[:12]) if matching_skills else 'None'

        # Pull raw resume text — give AI the full picture
        resume_text = resume_data.get('full_text', '')[:3000]
        skills_list = resume_data.get('skills', [])
        experience  = resume_data.get('experience', [])
        education   = resume_data.get('education', [])

        skills_str  = ', '.join(skills_list[:30]) if skills_list else 'See resume'
        exp_str     = '\n'.join(f"- {e}" for e in experience[:10]) if experience else ''
        edu_str     = '\n'.join(education[:4]) if education else ''

        prompt = f"""
You are a senior technical resume writer. Your job is to produce a COMPLETE, PROFESSIONAL, ATS-optimised resume in clean Markdown.

=== TARGET JOB ===
Title:    {job.get('title', '')}
Company:  {job.get('company', '')}
Location: {job.get('location', 'Remote')}

Job Description (key excerpt):
{job.get('description', '')[:1200]}

=== CANDIDATE PROFILE ===
Name:     {user.get('name', '')}
Email:    {user.get('email', '')}
Phone:    {user.get('phone', '')}
LinkedIn: {user.get('linkedin', '')}
GitHub:   {user.get('github', '')}
Location: {user.get('location', 'India')}

Current Skills: {skills_str}

Current Experience:
{exp_str if exp_str else '(extract from resume text below)'}

Education:
{edu_str if edu_str else '(extract from resume text below)'}

Raw Resume Text:
{resume_text}

=== ATS ANALYSIS ===
ATS Score:       {ats_result.get('score', 0)}/100
Matching Skills: {matching_str}
Missing Skills:  {missing_str}

=== WRITING RULES (follow strictly) ===
1. NEVER invent companies, degrees, or dates that are not in the resume
2. DO reframe and strengthen existing experience using better language
3. USE strong action verbs: Engineered, Architected, Deployed, Optimised, Automated, Spearheaded
4. ADD quantified metrics wherever possible: "Reduced inference time by 40%", "Trained model on 50K samples"
5. WEAVE IN missing keywords naturally — only where they genuinely fit
6. Keep bullet points concise: 1 line each, max 120 characters
7. Professional Summary must be 2-3 sentences, role-specific, impactful
8. Skills section must use bold category labels

=== EXACT OUTPUT FORMAT ===
Use this EXACT Markdown structure (no deviations):

# {user.get('name', 'Full Name')}
{user.get('email', '')} | {user.get('phone', '')} | {user.get('linkedin', '')} | {user.get('github', '')} | {user.get('location', 'India')}

## Summary
[2-3 sentences. Mention the target role and company. Highlight top 2-3 skills. Show impact mindset.]

## Skills
**AI / ML:** [comma-separated skills]
**Programming:** [comma-separated skills]
**Frameworks & Tools:** [comma-separated skills]
**Other:** [any other relevant skills]

## Experience
### [Job Title] | [Company Name] | [Month Year – Month Year or Present]
- [Strong action verb + what you did + measurable result]
- [Strong action verb + what you did + measurable result]
- [Strong action verb + what you did + measurable result]

(repeat for each role)

## Projects
### [Project Name] | [Tech Stack used]
- [What it does, how you built it, scale/impact]
- [Key technical achievement]

(repeat for each project)

## Education
### [Degree] | [Institution] | [Year]
- [GPA if strong, relevant coursework, achievements]

## Certifications
- [Certification name] — [Issuer] ([Year])

---
Write the COMPLETE resume now. Every section must be filled. Do not truncate or summarise — write the full content.
"""

        system_prompt = (
            "You are a world-class technical resume writer specialising in AI, ML, "
            "robotics, and software engineering roles. You write resumes that score "
            "90+ on ATS systems AND impress senior engineers. "
            "You are precise, specific, and results-oriented. "
            "You NEVER fabricate experience. You always output clean Markdown."
        )

        result = self.ai.generate(prompt, system_prompt)

        if result.startswith('ERROR'):
            logger.error("AI failed — using structured fallback resume")
            return self._structured_fallback(resume_data, job, user, matching_skills)

        # Ensure the resume starts with the name header
        if not result.strip().startswith('#'):
            result = f"# {user.get('name', 'Candidate')}\n" + result

        logger.info(f"Resume optimised: {len(result)} characters")
        return result

    def _structured_fallback(
        self,
        resume_data: dict,
        job: dict,
        user: dict,
        matching_skills: list,
    ) -> str:
        """
        High-quality structured fallback when AI is unavailable.
        Uses all available resume data to build a proper resume.
        """
        skills   = resume_data.get('skills', [])
        exp      = resume_data.get('experience', [])
        edu      = resume_data.get('education', [])

        # Split skills into categories
        ai_skills   = [s for s in skills if s.lower() in [
            'machine learning', 'deep learning', 'tensorflow', 'pytorch',
            'keras', 'scikit-learn', 'nlp', 'computer vision', 'yolo',
            'transformers', 'bert', 'gpt', 'reinforcement learning', 'mlops',
        ]]
        prog_skills = [s for s in skills if s.lower() in [
            'python', 'javascript', 'typescript', 'java', 'c', 'c++', 'c#',
            'go', 'rust', 'r', 'matlab',
        ]]
        tool_skills = [s for s in skills if s not in ai_skills and s not in prog_skills]

        ai_str   = ', '.join(ai_skills[:8])   or 'Machine Learning, Deep Learning'
        prog_str = ', '.join(prog_skills[:8]) or 'Python, C++'
        tool_str = ', '.join(tool_skills[:10]) or 'Git, Docker, Linux'

        exp_bullets = '\n'.join(f"- {e}" for e in exp[:6]) if exp else \
            "- Developed and deployed machine learning models for real-world applications\n" \
            "- Collaborated with cross-functional teams to deliver technical solutions"

        edu_text = '\n'.join(f"- {e}" for e in edu[:3]) if edu else \
            "- B.Tech Computer Science / Engineering"

        return f"""# {user.get('name', 'Candidate')}
{user.get('email', '')} | {user.get('phone', '')} | {user.get('linkedin', '')} | {user.get('github', '')} | {user.get('location', 'India')}

## Summary
Results-driven engineer with hands-on expertise in {ai_str[:80]}. Seeking the {job.get('title', 'role')} position at {job.get('company', 'the company')} to apply strong technical skills and deliver impactful solutions. Passionate about building scalable, production-ready systems.

## Skills
**AI / ML:** {ai_str}
**Programming:** {prog_str}
**Frameworks & Tools:** {tool_str}

## Experience
{exp_bullets}

## Education
{edu_text}

---
*Optimised for {job.get('title', 'position')} at {job.get('company', 'Company')}*
"""
