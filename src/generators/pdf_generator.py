"""
============================================================
src/generators/pdf_generator.py
------------------------------------------------------------
PURPOSE:
    Generates professional, ATS-friendly PDF resumes and
    cover letters using ReportLab with a clean modern layout.

DESIGN:
    - Clean two-column header (name + contact)
    - Colored section dividers
    - Consistent typography (Helvetica family)
    - Proper spacing and margins
    - ATS-readable (no tables, no images, no columns)
============================================================
"""

import re
from pathlib import Path
from datetime import datetime
from loguru import logger


class PDFGenerator:
    """
    Generates professional PDF files from Markdown text.
    """

    # Brand color — deep navy blue
    ACCENT_COLOR = '#1B3A6B'
    TEXT_COLOR   = '#1a1a1a'
    MUTED_COLOR  = '#555555'

    def __init__(self, config: dict):
        self.config = config
        pdf_cfg = config.get('pdf', {})
        self.output_dir = Path(pdf_cfg.get('output_dir', 'data/pdfs'))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.user = config.get('user', {})

    # ----------------------------------------------------------
    # PUBLIC API
    # ----------------------------------------------------------

    def generate_resume_pdf(self, markdown_text: str, job: dict) -> str:
        """Generates a professional resume PDF from Markdown text."""
        company   = re.sub(r'[^\w\s-]', '', job.get('company', 'Company')).replace(' ', '_')[:20]
        title     = re.sub(r'[^\w\s-]', '', job.get('title',   'Position')).replace(' ', '_')[:20]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename  = f"resume_{company}_{title}_{timestamp}.pdf"
        out_path  = str(self.output_dir / filename)

        logger.info(f"Generating resume PDF: {filename}")

        ok = self._build_resume_pdf(markdown_text, out_path)
        if ok:
            logger.info(f"Resume PDF saved: {out_path}")
            return out_path
        logger.error("Failed to generate resume PDF")
        return ""

    def generate_cover_letter_pdf(self, text: str, job: dict) -> str:
        """Generates a professional cover letter PDF."""
        company   = re.sub(r'[^\w\s-]', '', job.get('company', 'Company')).replace(' ', '_')[:20]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename  = f"cover_letter_{company}_{timestamp}.pdf"
        out_path  = str(self.output_dir / filename)

        logger.info(f"Generating cover letter PDF: {filename}")

        ok = self._build_cover_letter_pdf(text, out_path, job)
        if ok:
            logger.info(f"Cover letter PDF saved: {out_path}")
            return out_path
        logger.error("Failed to generate cover letter PDF")
        return ""

    # ----------------------------------------------------------
    # RESUME PDF BUILDER
    # ----------------------------------------------------------

    def _build_resume_pdf(self, markdown_text: str, output_path: str) -> bool:
        """Builds a clean, professional resume PDF."""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import ParagraphStyle
            from reportlab.lib.units import cm, mm
            from reportlab.lib import colors
            from reportlab.platypus import (
                SimpleDocTemplate, Paragraph, Spacer,
                HRFlowable, KeepTogether
            )
            from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY

            accent  = colors.HexColor(self.ACCENT_COLOR)
            text_c  = colors.HexColor(self.TEXT_COLOR)
            muted_c = colors.HexColor(self.MUTED_COLOR)
            light_c = colors.HexColor('#E8EDF5')

            # ---- Document setup ----
            doc = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                leftMargin=1.8 * cm,
                rightMargin=1.8 * cm,
                topMargin=1.5 * cm,
                bottomMargin=1.5 * cm,
            )

            # ---- Style definitions ----
            s_name = ParagraphStyle(
                'Name',
                fontSize=22, fontName='Helvetica-Bold',
                textColor=accent, alignment=TA_LEFT,
                spaceAfter=2,
            )
            s_contact = ParagraphStyle(
                'Contact',
                fontSize=8.5, fontName='Helvetica',
                textColor=muted_c, alignment=TA_LEFT,
                spaceAfter=6, leading=13,
            )
            s_section = ParagraphStyle(
                'Section',
                fontSize=10, fontName='Helvetica-Bold',
                textColor=accent, alignment=TA_LEFT,
                spaceBefore=10, spaceAfter=3,
                textTransform='uppercase',
            )
            s_job_title = ParagraphStyle(
                'JobTitle',
                fontSize=10, fontName='Helvetica-Bold',
                textColor=text_c, alignment=TA_LEFT,
                spaceBefore=5, spaceAfter=1,
            )
            s_job_meta = ParagraphStyle(
                'JobMeta',
                fontSize=8.5, fontName='Helvetica-Oblique',
                textColor=muted_c, alignment=TA_LEFT,
                spaceAfter=2,
            )
            s_bullet = ParagraphStyle(
                'Bullet',
                fontSize=9, fontName='Helvetica',
                textColor=text_c, alignment=TA_JUSTIFY,
                leftIndent=12, firstLineIndent=-8,
                spaceAfter=2, leading=13,
            )
            s_body = ParagraphStyle(
                'Body',
                fontSize=9, fontName='Helvetica',
                textColor=text_c, alignment=TA_JUSTIFY,
                spaceAfter=3, leading=13,
            )
            s_skills_label = ParagraphStyle(
                'SkillsLabel',
                fontSize=9, fontName='Helvetica-Bold',
                textColor=text_c, alignment=TA_LEFT,
                spaceAfter=2, leading=13,
            )

            def hr():
                return HRFlowable(
                    width='100%', thickness=0.8,
                    color=accent, spaceAfter=4, spaceBefore=2,
                )

            def thin_hr():
                return HRFlowable(
                    width='100%', thickness=0.3,
                    color=colors.HexColor('#CCCCCC'),
                    spaceAfter=3, spaceBefore=3,
                )

            # ---- Parse markdown into elements ----
            elements = []
            lines = markdown_text.strip().split('\n')

            # Extract name and contact from first few lines
            name_line    = ''
            contact_line = ''
            body_start   = 0

            for idx, line in enumerate(lines):
                s = line.strip()
                if s.startswith('# '):
                    name_line  = s[2:].strip()
                    body_start = idx + 1
                    break

            # Contact line is usually right after the name
            for idx in range(body_start, min(body_start + 3, len(lines))):
                s = lines[idx].strip()
                if s and not s.startswith('#') and ('|' in s or '@' in s or '+' in s):
                    contact_line = s
                    body_start   = idx + 1
                    break

            # Render name + contact header
            if name_line:
                elements.append(Paragraph(name_line, s_name))
            if contact_line:
                # Clean up markdown links
                clean_contact = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', contact_line)
                # Replace | with  ·  for readability
                clean_contact = clean_contact.replace(' | ', '   ·   ')
                elements.append(Paragraph(clean_contact, s_contact))

            elements.append(hr())

            # Parse remaining lines
            i = body_start
            while i < len(lines):
                line = lines[i]
                s    = line.strip()

                if not s:
                    elements.append(Spacer(1, 3))
                    i += 1
                    continue

                # ## Section header
                if s.startswith('## '):
                    section_name = s[3:].strip()
                    elements.append(Spacer(1, 4))
                    elements.append(Paragraph(section_name, s_section))
                    elements.append(hr())

                # ### Job title / project title
                elif s.startswith('### '):
                    sub = s[4:].strip()
                    # Split "Title | Company | Date" into title and meta
                    parts = [p.strip() for p in sub.split('|')]
                    if len(parts) >= 2:
                        title_text = parts[0]
                        meta_text  = '  ·  '.join(parts[1:])
                        block = [
                            Paragraph(self._md_inline(title_text), s_job_title),
                            Paragraph(self._md_inline(meta_text),  s_job_meta),
                        ]
                    else:
                        block = [Paragraph(self._md_inline(sub), s_job_title)]
                    elements.append(KeepTogether(block))

                # Bullet point
                elif s.startswith('- ') or s.startswith('* '):
                    text = self._md_inline(s[2:].strip())
                    elements.append(Paragraph(f'&#8226; {text}', s_bullet))

                # Skills line: **Category:** items
                elif s.startswith('**') and ':' in s:
                    text = self._md_inline(s)
                    elements.append(Paragraph(text, s_skills_label))

                # Regular paragraph
                else:
                    text = self._md_inline(s)
                    elements.append(Paragraph(text, s_body))

                i += 1

            doc.build(elements)
            return True

        except Exception as e:
            logger.error(f"Resume PDF build failed: {e}")
            return self._fpdf_fallback(markdown_text, output_path)

    # ----------------------------------------------------------
    # COVER LETTER PDF BUILDER
    # ----------------------------------------------------------

    def _build_cover_letter_pdf(self, text: str, output_path: str, job: dict) -> bool:
        """Builds a clean cover letter PDF."""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import ParagraphStyle
            from reportlab.lib.units import cm
            from reportlab.lib import colors
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
            from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY

            accent  = colors.HexColor(self.ACCENT_COLOR)
            text_c  = colors.HexColor(self.TEXT_COLOR)
            muted_c = colors.HexColor(self.MUTED_COLOR)

            doc = SimpleDocTemplate(
                output_path, pagesize=A4,
                leftMargin=2.5*cm, rightMargin=2.5*cm,
                topMargin=2*cm, bottomMargin=2*cm,
            )

            s_header = ParagraphStyle(
                'Header', fontSize=14, fontName='Helvetica-Bold',
                textColor=accent, spaceAfter=2,
            )
            s_sub = ParagraphStyle(
                'Sub', fontSize=9, fontName='Helvetica',
                textColor=muted_c, spaceAfter=12,
            )
            s_body = ParagraphStyle(
                'Body', fontSize=10, fontName='Helvetica',
                textColor=text_c, leading=16,
                spaceAfter=10, alignment=TA_JUSTIFY,
            )
            s_sig = ParagraphStyle(
                'Sig', fontSize=10, fontName='Helvetica-Bold',
                textColor=text_c, spaceAfter=2,
            )

            elements = []

            # Header: name + contact
            name = self.user.get('name', '')
            if name:
                elements.append(Paragraph(name, s_header))
                contact_parts = []
                if self.user.get('email'):    contact_parts.append(self.user['email'])
                if self.user.get('phone'):    contact_parts.append(self.user['phone'])
                if self.user.get('linkedin'): contact_parts.append(self.user['linkedin'])
                elements.append(Paragraph('   ·   '.join(contact_parts), s_sub))
                elements.append(HRFlowable(
                    width='100%', thickness=0.8, color=accent, spaceAfter=14,
                ))

            # Body paragraphs
            paragraphs = [p.strip() for p in text.strip().split('\n\n') if p.strip()]
            for para in paragraphs:
                # Skip lines that are just the name/contact (already in header)
                if para == name:
                    continue
                # Detect signature block
                if para.lower().startswith(('sincerely', 'best regards', 'regards', 'yours')):
                    elements.append(Spacer(1, 20))
                    for sig_line in para.split('\n'):
                        if sig_line.strip():
                            elements.append(Paragraph(sig_line.strip(), s_sig))
                else:
                    clean = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', para)
                    clean = re.sub(r'\*(.+?)\*', r'<i>\1</i>', clean)
                    clean = clean.replace('\n', ' ')
                    elements.append(Paragraph(clean, s_body))

            doc.build(elements)
            return True

        except Exception as e:
            logger.error(f"Cover letter PDF build failed: {e}")
            return self._fpdf_fallback(text, output_path)

    # ----------------------------------------------------------
    # HELPERS
    # ----------------------------------------------------------

    def _md_inline(self, text: str) -> str:
        """Convert inline Markdown to ReportLab XML tags."""
        # Escape & < > first to avoid XML errors
        text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        # **bold**
        text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
        # *italic*
        text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
        # `code`
        text = re.sub(r'`(.+?)`', r'\1', text)
        # [text](url) → text
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        return text

    def _fpdf_fallback(self, text: str, output_path: str) -> bool:
        """Simple FPDF2 fallback when ReportLab fails."""
        try:
            from fpdf import FPDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.set_margins(18, 15, 18)

            # Strip markdown
            clean = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
            clean = re.sub(r'\*(.+?)\*',     r'\1', clean)
            clean = re.sub(r'`(.+?)`',        r'\1', clean)
            clean = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', clean)

            for line in clean.split('\n'):
                s = line.strip()
                if not s:
                    pdf.ln(3)
                elif line.startswith('# '):
                    pdf.set_font('Helvetica', 'B', 18)
                    pdf.set_text_color(27, 58, 107)
                    pdf.cell(0, 9, s[2:], ln=True)
                    pdf.set_text_color(0, 0, 0)
                elif line.startswith('## '):
                    pdf.set_font('Helvetica', 'B', 11)
                    pdf.set_text_color(27, 58, 107)
                    pdf.ln(4)
                    pdf.cell(0, 6, s[3:].upper(), ln=True)
                    pdf.set_draw_color(27, 58, 107)
                    pdf.line(18, pdf.get_y(), 192, pdf.get_y())
                    pdf.set_text_color(0, 0, 0)
                    pdf.ln(2)
                elif line.startswith('### '):
                    pdf.set_font('Helvetica', 'B', 10)
                    pdf.cell(0, 5, s[4:], ln=True)
                elif s.startswith('- ') or s.startswith('* '):
                    pdf.set_font('Helvetica', '', 9)
                    pdf.cell(6, 5, '')
                    pdf.multi_cell(0, 5, f"• {s[2:]}")
                else:
                    pdf.set_font('Helvetica', '', 9)
                    pdf.multi_cell(0, 5, s)

            pdf.output(output_path)
            return True
        except Exception as e:
            logger.error(f"FPDF fallback also failed: {e}")
            return False
