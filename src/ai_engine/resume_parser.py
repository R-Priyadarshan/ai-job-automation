"""
============================================================
src/ai_engine/resume_parser.py
------------------------------------------------------------
PURPOSE:
    Reads and parses the user's resume from various formats:
    - Plain text (.txt) — simplest format
    - PDF (.pdf)        — using pdfminer
    - Word (.docx)      — using python-docx

    After parsing, it extracts:
    - Skills list
    - Work experience sections
    - Education
    - Contact info
    - Full resume text (for AI processing)

WHY WE NEED THIS:
    The AI needs to read your resume to compare it with
    job descriptions. This module converts your resume
    into plain text that the AI can understand.
============================================================
"""

import re                        # Regular expressions
from pathlib import Path         # File path handling
from loguru import logger        # Logging


class ResumeParser:
    """
    Parses resumes from multiple file formats and
    extracts structured information.
    """

    def __init__(self):
        """Initialize the resume parser."""
        # Common technical skills to detect in resumes
        # (Used for keyword extraction)
        self.tech_skills = [
            # Programming Languages
            'Python', 'JavaScript', 'TypeScript', 'Java', 'C', 'C++', 'C#',
            'Go', 'Rust', 'Ruby', 'PHP', 'Swift', 'Kotlin', 'Scala', 'R',
            'MATLAB', 'Verilog', 'VHDL', 'Assembly',

            # AI / ML
            'Machine Learning', 'Deep Learning', 'Neural Networks',
            'TensorFlow', 'PyTorch', 'Keras', 'Scikit-learn', 'XGBoost',
            'Computer Vision', 'NLP', 'Natural Language Processing',
            'OpenCV', 'YOLO', 'Transformers', 'BERT', 'GPT', 'LLM',
            'Reinforcement Learning', 'MLOps', 'Data Science',

            # Robotics / Embedded
            'ROS', 'ROS2', 'Arduino', 'Raspberry Pi', 'Embedded Systems',
            'FPGA', 'STM32', 'Microcontroller', 'PLC', 'RTOS',
            'Robotics', 'Autonomous Vehicles', 'Sensors', 'Actuators',

            # Web / Backend
            'React', 'Vue', 'Angular', 'Next.js', 'Node.js',
            'Django', 'Flask', 'FastAPI', 'Spring Boot', 'Express',
            'REST API', 'GraphQL', 'WebSocket',

            # Cloud / DevOps
            'Docker', 'Kubernetes', 'AWS', 'GCP', 'Azure',
            'CI/CD', 'GitHub Actions', 'Jenkins', 'Terraform', 'Ansible',
            'Linux', 'Bash', 'Shell Scripting',

            # Databases
            'SQL', 'PostgreSQL', 'MySQL', 'MongoDB', 'Redis',
            'SQLite', 'Elasticsearch', 'Cassandra',

            # Tools
            'Git', 'GitHub', 'GitLab', 'JIRA', 'Confluence',
            'Jupyter', 'VS Code', 'PyCharm', 'Linux', 'Ubuntu',
        ]

    def parse(self, file_path: str) -> dict:
        """
        Main method — parses a resume file and returns structured data.

        Args:
            file_path: Path to the resume file (.txt, .pdf, or .docx)

        Returns:
            Dictionary with:
            {
                'full_text': str,        — Complete resume text
                'skills': list[str],     — Extracted skills
                'experience': list[str], — Experience bullet points
                'education': list[str],  — Education items
                'contact': dict,         — Name, email, phone, etc.
                'file_path': str,        — Original file path
            }
        """
        path = Path(file_path)

        if not path.exists():
            logger.error(f"Resume file not found: {file_path}")
            return self._empty_resume(file_path)

        # Determine file format and parse accordingly
        extension = path.suffix.lower()

        if extension == '.txt':
            text = self._parse_txt(path)
        elif extension == '.pdf':
            text = self._parse_pdf(path)
        elif extension in ['.docx', '.doc']:
            text = self._parse_docx(path)
        else:
            logger.warning(f"Unsupported resume format: {extension}. Treating as text.")
            text = self._parse_txt(path)

        if not text:
            logger.error(f"Could not extract text from: {file_path}")
            return self._empty_resume(file_path)

        # Extract structured information from the raw text
        result = {
            'full_text':   text,
            'skills':      self._extract_skills(text),
            'experience':  self._extract_experience(text),
            'education':   self._extract_education(text),
            'contact':     self._extract_contact(text),
            'file_path':   str(file_path),
        }

        logger.info(
            f"Resume parsed: {len(result['skills'])} skills, "
            f"{len(result['experience'])} experience items"
        )
        return result

    # =====================================================
    # FILE PARSERS
    # =====================================================

    def _parse_txt(self, path: Path) -> str:
        """Reads a plain text file."""
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to read text file: {e}")
            return ''

    def _parse_pdf(self, path: Path) -> str:
        """
        Extracts text from a PDF using pdfminer.
        Falls back to PyPDF2 if pdfminer fails.
        """
        # Try pdfminer first (better text extraction)
        try:
            from pdfminer.high_level import extract_text
            text = extract_text(str(path))
            if text:
                return text.strip()
        except ImportError:
            logger.warning("pdfminer not available, trying PyPDF2...")
        except Exception as e:
            logger.warning(f"pdfminer failed: {e}, trying PyPDF2...")

        # Fallback: PyPDF2
        try:
            import PyPDF2
            text_parts = []
            with open(path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text_parts.append(page.extract_text())
            return '\n'.join(text_parts)
        except Exception as e:
            logger.error(f"Failed to read PDF: {e}")
            return ''

    def _parse_docx(self, path: Path) -> str:
        """Extracts text from a Word .docx file."""
        try:
            from docx import Document
            doc = Document(str(path))
            paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
            return '\n'.join(paragraphs)
        except ImportError:
            logger.error("python-docx not installed. Run: pip install python-docx")
            return ''
        except Exception as e:
            logger.error(f"Failed to read DOCX: {e}")
            return ''

    # =====================================================
    # INFORMATION EXTRACTORS
    # =====================================================

    def _extract_skills(self, text: str) -> list[str]:
        """
        Extracts technical skills from resume text using keyword matching.

        Args:
            text: Full resume text.

        Returns:
            List of found skill names.
        """
        found_skills = []
        text_lower = text.lower()

        for skill in self.tech_skills:
            # Check for exact word match (not substring)
            # E.g., "C" shouldn't match inside "CI/CD"
            pattern = r'\b' + re.escape(skill.lower()) + r'\b'
            if re.search(pattern, text_lower):
                found_skills.append(skill)

        return found_skills

    def _extract_experience(self, text: str) -> list[str]:
        """
        Extracts work experience bullet points from resume text.

        Looks for common patterns:
        - Lines starting with action verbs (Developed, Built, Led, etc.)
        - Lines after "Experience" or "Work History" headers

        Args:
            text: Full resume text.

        Returns:
            List of experience strings.
        """
        lines = text.split('\n')
        experience_items = []

        # Common action verbs used in resume bullets
        action_verbs = [
            'developed', 'built', 'created', 'designed', 'implemented',
            'led', 'managed', 'deployed', 'optimized', 'improved',
            'researched', 'analyzed', 'automated', 'trained', 'achieved',
            'reduced', 'increased', 'launched', 'maintained', 'collaborated',
            'integrated', 'architected', 'engineered', 'programmed',
        ]

        # Flags to track if we're in experience section
        in_experience_section = False

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if we've hit an experience section header
            lower_line = line.lower()
            if any(h in lower_line for h in ['experience', 'work history', 'employment']):
                in_experience_section = True
                continue

            # Check if we've left experience section
            if in_experience_section and any(
                h in lower_line for h in ['education', 'skills', 'projects', 'certifications']
            ):
                in_experience_section = False

            # Collect lines that start with action verbs (likely bullets)
            words = lower_line.split()
            if words and words[0] in action_verbs:
                experience_items.append(line)

            # Also collect lines if we're in experience section
            elif in_experience_section and len(line) > 20 and line[0] in ['•', '-', '*', '·']:
                experience_items.append(line.lstrip('•-*· '))

        return experience_items[:20]  # Limit to 20 items

    def _extract_education(self, text: str) -> list[str]:
        """
        Extracts education information from resume text.

        Args:
            text: Full resume text.

        Returns:
            List of education entries.
        """
        lines = text.split('\n')
        education_items = []
        in_education = False

        # Common degree keywords
        degrees = ['b.tech', 'b.e.', 'm.tech', 'm.sc', 'mba', 'phd', 'bachelor',
                   'master', 'diploma', 'b.sc', 'b.com', 'bca', 'mca']

        for line in lines:
            line = line.strip()
            lower = line.lower()

            if 'education' in lower or 'academic' in lower:
                in_education = True
                continue

            if in_education and any(
                s in lower for s in ['experience', 'skills', 'projects']
            ):
                in_education = False

            if in_education and line and len(line) > 5:
                education_items.append(line)

            # Also catch degree lines anywhere in document
            if any(deg in lower for deg in degrees) and line not in education_items:
                education_items.append(line)

        return list(dict.fromkeys(education_items))[:10]  # Deduplicate, limit 10

    def _extract_contact(self, text: str) -> dict:
        """
        Extracts contact information from resume text.

        Args:
            text: Full resume text.

        Returns:
            Dict with name, email, phone, linkedin, github.
        """
        contact = {
            'name': '',
            'email': '',
            'phone': '',
            'linkedin': '',
            'github': '',
        }

        # Email: standard regex pattern
        email_match = re.search(r'[\w.+-]+@[\w-]+\.[\w.]+', text)
        if email_match:
            contact['email'] = email_match.group()

        # Phone: various Indian/international formats
        phone_match = re.search(
            r'(?:\+91[-\s]?)?[6-9]\d{9}|'      # Indian mobile
            r'\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',  # International
            text
        )
        if phone_match:
            contact['phone'] = phone_match.group().strip()

        # LinkedIn URL
        linkedin_match = re.search(r'linkedin\.com/in/[\w-]+', text, re.IGNORECASE)
        if linkedin_match:
            contact['linkedin'] = 'https://' + linkedin_match.group()

        # GitHub URL
        github_match = re.search(r'github\.com/[\w-]+', text, re.IGNORECASE)
        if github_match:
            contact['github'] = 'https://' + github_match.group()

        # Name: Usually the first non-empty line of a resume
        first_line = text.strip().split('\n')[0].strip()
        if first_line and len(first_line.split()) <= 5 and not '@' in first_line:
            contact['name'] = first_line

        return contact

    def _empty_resume(self, file_path: str) -> dict:
        """Returns an empty resume structure on failure."""
        return {
            'full_text':  '',
            'skills':     [],
            'experience': [],
            'education':  [],
            'contact':    {'name': '', 'email': '', 'phone': '', 'linkedin': '', 'github': ''},
            'file_path':  str(file_path),
        }
