"""
============================================================
src/generators/pdf_generator.py
------------------------------------------------------------
PURPOSE:
    Converts Markdown-formatted text (resume/cover letter)
    into professional PDF files.

WHY PDF?
    - Professional format for resumes
    - Preserves formatting across all systems
    - Standard format for job applications
    - Works with ATS systems (PDFs are readable by modern ATS)

HOW IT WORKS:
    1. Takes Markdown text input
    2. Parses Markdown structure (headers, bullets, bold, etc.)
    3. Uses ReportLab to generate a styled PDF
    4. Saves PDF to the output directory

LIBRARIES USED:
    - reportlab: Full-featured PDF generation (free, open source)
    - fpdf2: Simpler alternative (fallback if reportlab unavailable)

WHY NOT WEASYPRINT/PUPPETEER?
    Those require system-level dependencies.
    ReportLab is pure Python — works everywhere.
============================================================
"""

import re                            # Regular expressions
from pathlib import Path             # Path handling
from datetime import datetime        # Timestamps
from loguru import logger            # Logging


class PDFGenerator:
    """
    Generates professional PDF files from Markdown text.
    Used for both resumes and cover letters.
    """

    def __init__(self, config: dict):
        """
        Initialize PDF generator.

        Args:
            config: Config dict from config.yaml
        """
        self.config = config
        pdf_cfg = config.get('pdf', {})
        self.output_dir = Path(pdf_cfg.get('output_dir', 'data/pdfs'))
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_resume_pdf(self, markdown_text: str, job: dict) -> str:
        """
        Generates a professional resume PDF from Markdown text.

        Args:
            markdown_text: Resume in Markdown format.
            job: Job dict (used for naming the file).

        Returns:
            Absolute path to the generated PDF file.
        """
        # Create safe filename from job title and company
        company = re.sub(r'[^\w\s-]', '', job.get('company', 'Company'))
        title = re.sub(r'[^\w\s-]', '', job.get('title', 'Position'))
        company = company.replace(' ', '_')[:20]
        title = title.replace(' ', '_')[:20]

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"resume_{company}_{title}_{timestamp}.pdf"
        output_path = self.output_dir / filename

        logger.info(f"Generating resume PDF: {filename}")

        # Try ReportLab first (better quality)
        success = self._generate_with_reportlab(
            text=markdown_text,
            output_path=str(output_path),
            doc_type='resume',
            title=f"Resume — {title} at {company}",
        )

        if not success:
            # Fallback to FPDF2
            success = self._generate_with_fpdf(
                text=markdown_text,
                output_path=str(output_path),
                doc_type='resume',
            )

        if success:
            logger.info(f"Resume PDF saved: {output_path}")
            return str(output_path)
        else:
            logger.error("Failed to generate resume PDF")
            return ""

    def generate_cover_letter_pdf(self, text: str, job: dict) -> str:
        """
        Generates a professional cover letter PDF.

        Args:
            text: Cover letter text (plain or Markdown).
            job: Job dict (used for naming the file).

        Returns:
            Absolute path to the generated PDF file.
        """
        company = re.sub(r'[^\w\s-]', '', job.get('company', 'Company'))
        company = company.replace(' ', '_')[:20]

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"cover_letter_{company}_{timestamp}.pdf"
        output_path = self.output_dir / filename

        logger.info(f"Generating cover letter PDF: {filename}")

        success = self._generate_with_reportlab(
            text=text,
            output_path=str(output_path),
            doc_type='cover_letter',
            title=f"Cover Letter — {job.get('company', 'Company')}",
        )

        if not success:
            success = self._generate_with_fpdf(
                text=text,
                output_path=str(output_path),
                doc_type='cover_letter',
            )

        if success:
            logger.info(f"Cover letter PDF saved: {output_path}")
            return str(output_path)
        else:
            logger.error("Failed to generate cover letter PDF")
            return ""

    def _generate_with_reportlab(
        self, text: str, output_path: str, doc_type: str, title: str
    ) -> bool:
        """
        Generates PDF using ReportLab library.
        ReportLab gives fine-grained control over PDF layout.

        Args:
            text: Document text (Markdown format).
            output_path: Where to save the PDF.
            doc_type: 'resume' or 'cover_letter'.
            title: Document title (metadata).

        Returns:
            True if successful, False otherwise.
        """
        try:
            from reportlab.lib.pagesizes import A4, letter
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch, cm
            from reportlab.lib import colors
            from reportlab.platypus import (
                SimpleDocTemplate, Paragraph, Spacer, HRFlowable, ListFlowable, ListItem
            )
            from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY

        except ImportError:
            logger.warning("ReportLab not installed. Run: pip install reportlab")
            return False

        try:
            # Create the PDF document
            # A4 size with 1.5cm margins
            doc = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                rightMargin=1.5 * cm,
                leftMargin=1.5 * cm,
                topMargin=1.5 * cm,
                bottomMargin=1.5 * cm,
                title=title,
                author="AI Job Application System",
            )

            # Define styles for different text elements
            styles = getSampleStyleSheet()

            # Custom styles for professional look
            style_name = ParagraphStyle(
                'CandidateName',
                parent=styles['Normal'],
                fontSize=20,
                fontName='Helvetica-Bold',
                textColor=colors.HexColor('#1a1a2e'),   # Dark navy
                spaceAfter=4,
                alignment=TA_CENTER,
            )

            style_contact = ParagraphStyle(
                'ContactInfo',
                parent=styles['Normal'],
                fontSize=9,
                fontName='Helvetica',
                textColor=colors.HexColor('#4a4a6a'),
                spaceAfter=8,
                alignment=TA_CENTER,
            )

            style_section_header = ParagraphStyle(
                'SectionHeader',
                parent=styles['Normal'],
                fontSize=11,
                fontName='Helvetica-Bold',
                textColor=colors.HexColor('#2c3e7a'),   # Professional blue
                spaceBefore=10,
                spaceAfter=4,
                borderPadding=(0, 0, 2, 0),
            )

            style_h3 = ParagraphStyle(
                'JobTitle',
                parent=styles['Normal'],
                fontSize=10,
                fontName='Helvetica-Bold',
                textColor=colors.HexColor('#1a1a2e'),
                spaceBefore=6,
                spaceAfter=2,
            )

            style_body = ParagraphStyle(
                'Body',
                parent=styles['Normal'],
                fontSize=9.5,
                fontName='Helvetica',
                textColor=colors.HexColor('#2d2d2d'),
                spaceAfter=4,
                leading=13,
                alignment=TA_JUSTIFY,
            )

            style_bullet = ParagraphStyle(
                'Bullet',
                parent=styles['Normal'],
                fontSize=9.5,
                fontName='Helvetica',
                textColor=colors.HexColor('#2d2d2d'),
                spaceAfter=2,
                leading=13,
                leftIndent=15,
                bulletIndent=5,
            )

            # Build the content elements list
            elements = []

            # Parse Markdown and build PDF elements
            lines = text.split('\n')
            i = 0

            while i < len(lines):
                line = lines[i]
                stripped = line.strip()

                if not stripped:
                    # Blank line — add small spacer
                    elements.append(Spacer(1, 4))
                    i += 1
                    continue

                # H1 — Candidate name (# Name)
                if stripped.startswith('# '):
                    name_text = stripped[2:].strip()
                    elements.append(Paragraph(name_text, style_name))

                # H2 — Section headers (## Experience)
                elif stripped.startswith('## '):
                    section = stripped[3:].strip()
                    # Add horizontal line before section
                    elements.append(Spacer(1, 4))
                    elements.append(HRFlowable(
                        width="100%",
                        thickness=0.5,
                        color=colors.HexColor('#2c3e7a'),
                        spaceAfter=4,
                    ))
                    elements.append(Paragraph(section.upper(), style_section_header))

                # H3 — Job titles within sections (### Developer | Company)
                elif stripped.startswith('### '):
                    sub = stripped[4:].strip()
                    # Replace | with bullet separator
                    sub = sub.replace(' | ', '  ·  ')
                    elements.append(Paragraph(sub, style_h3))

                # Bullet points (- item or * item)
                elif stripped.startswith('- ') or stripped.startswith('* '):
                    bullet_text = stripped[2:].strip()
                    # Handle bold text in bullets (**text**)
                    bullet_text = self._convert_markdown_inline(bullet_text)
                    elements.append(Paragraph(f'• {bullet_text}', style_bullet))

                # Contact info line (contains @ or |)
                elif '@' in stripped or ('|' in stripped and i < 5):
                    # Convert markdown links to plain text
                    clean = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', stripped)
                    elements.append(Paragraph(clean, style_contact))

                # Regular paragraph
                else:
                    # Convert inline markdown
                    clean = self._convert_markdown_inline(stripped)
                    elements.append(Paragraph(clean, style_body))

                i += 1

            # Build the PDF
            doc.build(elements)
            return True

        except Exception as e:
            logger.error(f"ReportLab PDF generation failed: {e}")
            return False

    def _convert_markdown_inline(self, text: str) -> str:
        """
        Converts inline Markdown to ReportLab's XML-like markup.
        ReportLab Paragraphs support <b>, <i>, <u> tags.

        Args:
            text: Text with possible Markdown inline formatting.

        Returns:
            Text with ReportLab-compatible markup.
        """
        # **bold** → <b>bold</b>
        text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)

        # *italic* → <i>italic</i>
        text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)

        # `code` → just the text (no special formatting in PDF)
        text = re.sub(r'`(.+?)`', r'\1', text)

        # [link text](url) → link text (strip URL for PDF)
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)

        return text

    def _generate_with_fpdf(
        self, text: str, output_path: str, doc_type: str
    ) -> bool:
        """
        Fallback PDF generator using FPDF2.
        Simpler than ReportLab but still produces good results.

        Args:
            text: Document text.
            output_path: Where to save PDF.
            doc_type: 'resume' or 'cover_letter'.

        Returns:
            True if successful, False otherwise.
        """
        try:
            from fpdf import FPDF

            pdf = FPDF()
            pdf.add_page()
            pdf.set_auto_page_break(auto=True, margin=15)

            # Remove Markdown syntax for simple rendering
            clean_text = self._strip_markdown(text)

            lines = clean_text.split('\n')

            for line in lines:
                stripped = line.strip()
                if not stripped:
                    pdf.ln(3)
                    continue

                # Detect headers by original markdown patterns
                if line.startswith('# '):
                    pdf.set_font('Helvetica', 'B', 16)
                    pdf.cell(0, 8, line[2:].strip(), ln=True, align='C')
                elif line.startswith('## '):
                    pdf.set_font('Helvetica', 'B', 11)
                    pdf.set_text_color(44, 62, 122)
                    pdf.cell(0, 6, line[3:].strip().upper(), ln=True)
                    pdf.set_draw_color(44, 62, 122)
                    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                    pdf.set_text_color(0, 0, 0)
                    pdf.ln(2)
                elif line.startswith('### '):
                    pdf.set_font('Helvetica', 'B', 10)
                    pdf.cell(0, 5, line[4:].strip(), ln=True)
                elif stripped.startswith('- ') or stripped.startswith('* '):
                    pdf.set_font('Helvetica', '', 9)
                    pdf.cell(5, 5, '')  # Indent
                    pdf.multi_cell(0, 5, f"• {stripped[2:]}")
                else:
                    pdf.set_font('Helvetica', '', 9)
                    pdf.multi_cell(0, 5, stripped)

            pdf.output(output_path)
            return True

        except ImportError:
            logger.warning("fpdf2 not installed. Run: pip install fpdf2")
            return False
        except Exception as e:
            logger.error(f"FPDF2 generation failed: {e}")
            return False

    def _strip_markdown(self, text: str) -> str:
        """
        Strips Markdown formatting to get plain text.
        Used when we want to preserve structure but remove syntax.

        Args:
            text: Markdown text.

        Returns:
            Plain text.
        """
        # Remove bold markers
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        # Remove italic markers
        text = re.sub(r'\*(.+?)\*', r'\1', text)
        # Remove inline code
        text = re.sub(r'`(.+?)`', r'\1', text)
        # Convert links to text
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        # Remove horizontal rules
        text = re.sub(r'^---+$', '', text, flags=re.MULTILINE)

        return text
