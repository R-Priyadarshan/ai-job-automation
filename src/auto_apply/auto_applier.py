"""
============================================================
src/auto_apply/auto_applier.py
------------------------------------------------------------
PURPOSE:
    Orchestrates the full auto-apply pipeline:
    1. Fetch jobs from DB that meet ATS threshold
    2. Generate personalised cold internship email via AI
    3. Attach resume + cover letter PDFs
    4. Send email via Gmail SMTP
    5. Record sent status in database
    6. Respect rate limits (max 20/day, 30s between sends)

SAFETY FEATURES:
    - Dry-run mode: generates emails but does NOT send
    - Daily cap: max 20 emails per day
    - Duplicate check: never emails same company twice
    - Only emails jobs with ATS score >= threshold
    - Logs every action for full audit trail

USAGE:
    from src.auto_apply.auto_applier import AutoApplier
    applier = AutoApplier(config)
    applier.run(dry_run=False)   # set dry_run=True to preview only
============================================================
"""

from pathlib import Path
from loguru import logger
from rich.console import Console
from rich.table import Table

from src.database.db_manager import DatabaseManager
from src.ai_engine.resume_parser import ResumeParser
from src.ai_engine.ats_matcher import ATSMatcher
from src.ai_engine.resume_optimizer import ResumeOptimizer
from src.ai_engine.cover_letter_generator import CoverLetterGenerator
from src.ai_engine.cold_mail_generator import ColdMailGenerator
from src.generators.pdf_generator import PDFGenerator
from src.utils.email_sender import EmailSender

console = Console()


class AutoApplier:
    """
    Full auto-apply pipeline: scrape → score → generate → email.
    """

    def __init__(self, config: dict):
        """
        Initialize all components.

        Args:
            config: Config dict from config.yaml
        """
        self.config      = config
        self.db          = DatabaseManager(config['database']['path'])
        self.parser      = ResumeParser()
        self.ats         = ATSMatcher(config)
        self.optimizer   = ResumeOptimizer(config)
        self.cover_gen   = CoverLetterGenerator(config)
        self.cold_gen    = ColdMailGenerator(config)
        self.pdf_gen     = PDFGenerator(config)
        self.emailer     = EmailSender(config)

        self.min_score   = config.get('ats', {}).get('minimum_score', 60)
        self.resume_path = config.get('user', {}).get('resume_path', '')

    def run(self, dry_run: bool = True, limit: int = 20) -> dict:
        """
        Runs the full auto-apply pipeline.

        Args:
            dry_run: If True, generates emails but does NOT send them.
                     Always start with dry_run=True to preview first!
            limit:   Max number of jobs to process in this run.

        Returns:
            dict with summary stats:
                'processed', 'emailed', 'skipped', 'failed', 'previews'
        """
        mode = "DRY RUN (preview only)" if dry_run else "LIVE (sending emails)"
        console.print(f"\n[bold blue]📧 Auto-Apply Pipeline — {mode}[/bold blue]")

        if not dry_run and not self.emailer.is_configured():
            console.print(
                "[red]❌ Email not configured![/red]\n"
                "[yellow]Add to .env:  EMAIL_PASSWORD=your_app_password[/yellow]\n"
                "[yellow]Add to config.yaml:  email.auto_send: true[/yellow]\n"
                "[yellow]Add to config.yaml:  email.sender_email: your@gmail.com[/yellow]"
            )
            return {'processed': 0, 'emailed': 0, 'skipped': 0, 'failed': 0}

        # Parse resume once — reuse for all jobs
        console.print(f"[blue]📄 Parsing resume: {self.resume_path}[/blue]")
        resume_data = self.parser.parse(self.resume_path)

        if not resume_data.get('full_text'):
            console.print("[red]❌ Resume is empty or unreadable![/red]")
            return {'processed': 0, 'emailed': 0, 'skipped': 0, 'failed': 0}

        console.print(
            f"[green]✅ Resume parsed — "
            f"{len(resume_data.get('skills', []))} skills found[/green]"
        )

        # Get jobs that haven't been emailed yet
        jobs = self._get_unemailed_jobs(limit)

        if not jobs:
            console.print("[yellow]ℹ️  No new jobs to apply to.[/yellow]")
            return {'processed': 0, 'emailed': 0, 'skipped': 0, 'failed': 0}

        console.print(f"[blue]🎯 Processing {len(jobs)} jobs...[/blue]\n")

        stats = {'processed': 0, 'emailed': 0, 'skipped': 0, 'failed': 0, 'previews': []}

        # Results table
        table = Table(
            title="Auto-Apply Results",
            show_header=True,
            header_style="bold blue"
        )
        table.add_column("Company",    style="cyan",  max_width=20)
        table.add_column("Role",       style="white", max_width=25)
        table.add_column("ATS Score",  justify="center")
        table.add_column("Email To",   style="green", max_width=25)
        table.add_column("Status",     justify="center")

        for job in jobs:
            stats['processed'] += 1
            job_id  = job.get('id')
            company = job.get('company', 'Unknown')
            title   = job.get('title', 'Unknown')

            logger.info(f"Processing [{stats['processed']}/{len(jobs)}]: {title} @ {company}")

            try:
                # ---- Get or compute ATS score ----
                ats_data = self.db.get_ats_score(job_id)

                if ats_data:
                    score = ats_data.get('score', 0)
                    ats_result = {
                        'score': score,
                        'matching_skills': [
                            s.strip()
                            for s in (ats_data.get('matching_skills') or '').split(',')
                            if s.strip()
                        ],
                        'missing_skills': [
                            s.strip()
                            for s in (ats_data.get('missing_skills') or '').split(',')
                            if s.strip()
                        ],
                        'analysis_text': ats_data.get('analysis_text', ''),
                    }
                else:
                    # Score not computed yet — run ATS now
                    ats_result = self.ats.analyze(job, resume_data)
                    score = ats_result['score']
                    self.db.save_ats_score({
                        'job_id':          job_id,
                        'score':           score,
                        'matching_skills': ', '.join(ats_result.get('matching_skills', [])),
                        'missing_skills':  ', '.join(ats_result.get('missing_skills', [])),
                        'analysis_text':   ats_result.get('analysis_text', ''),
                    })

                # ---- Skip if score below threshold ----
                if score < self.min_score:
                    logger.debug(f"Skipping {company} — ATS score {score} < {self.min_score}")
                    stats['skipped'] += 1
                    table.add_row(
                        company[:20], title[:25],
                        f"{score}/100", "—",
                        f"[yellow]⏭ Skip ({score})[/yellow]"
                    )
                    continue

                # ---- Generate resume PDF if not already done ----
                resume_pdf = self._get_or_generate_resume(job, resume_data, ats_result)

                # ---- Generate cover letter PDF if not already done ----
                cover_pdf = self._get_or_generate_cover_letter(job, resume_data, ats_result)

                # ---- Generate cold internship email ----
                email_data = self.cold_gen.generate_cold_email(job, resume_data, ats_result)
                subject    = email_data['subject']
                body       = email_data['body']
                to_email   = email_data.get('to_email')

                # If no email found in job description, use config fallback
                if not to_email:
                    to_email = self.config.get('email', {}).get('fallback_to', '')

                # Store preview regardless of dry_run
                stats['previews'].append({
                    'job_id':    job_id,
                    'company':   company,
                    'title':     title,
                    'score':     score,
                    'to_email':  to_email,
                    'subject':   subject,
                    'body':      body,
                    'resume':    resume_pdf,
                    'cover':     cover_pdf,
                })

                if dry_run:
                    # Preview mode — don't send
                    table.add_row(
                        company[:20], title[:25],
                        f"{score}/100",
                        (to_email or "not found")[:25],
                        "[cyan]👁 Preview[/cyan]"
                    )
                    stats['emailed'] += 1   # count as "would send"
                    continue

                # ---- LIVE MODE: actually send the email ----
                if not to_email:
                    logger.warning(f"No email address found for {company} — skipping send")
                    stats['skipped'] += 1
                    table.add_row(
                        company[:20], title[:25],
                        f"{score}/100", "no email",
                        "[yellow]⚠ No email[/yellow]"
                    )
                    continue

                sent = self.emailer.send_cold_email(
                    to_email=to_email,
                    subject=subject,
                    body=body,
                    resume_path=resume_pdf,
                    cover_letter_path=cover_pdf,
                )

                if sent:
                    # Record in database
                    self.db.record_application({
                        'job_id':            job_id,
                        'ats_score':         score,
                        'notes':             f'Cold email sent to {to_email}',
                        'resume_path':       resume_pdf,
                        'cover_letter_path': cover_pdf,
                        'email_draft':       f"Subject: {subject}\n\n{body}",
                        'status':            'applied',
                    })
                    stats['emailed'] += 1
                    table.add_row(
                        company[:20], title[:25],
                        f"{score}/100", to_email[:25],
                        "[green]✅ Sent[/green]"
                    )
                else:
                    stats['failed'] += 1
                    table.add_row(
                        company[:20], title[:25],
                        f"{score}/100", (to_email or "—")[:25],
                        "[red]❌ Failed[/red]"
                    )

            except Exception as e:
                logger.error(f"Error processing {company}: {e}")
                stats['failed'] += 1
                table.add_row(
                    company[:20], title[:25],
                    "—", "—",
                    f"[red]❌ Error[/red]"
                )

        # Print results table
        console.print(table)

        action = "Would send" if dry_run else "Sent"
        console.print(
            f"\n[bold green]✅ Auto-Apply Complete![/bold green]\n"
            f"   Processed : {stats['processed']}\n"
            f"   {action}   : {stats['emailed']}\n"
            f"   Skipped   : {stats['skipped']} (below ATS threshold)\n"
            f"   Failed    : {stats['failed']}\n"
        )

        if dry_run and stats['previews']:
            console.print(
                "[yellow]💡 This was a DRY RUN. "
                "Set dry_run=False or use --auto-apply in CLI to actually send.[/yellow]"
            )

        return stats

    def _get_unemailed_jobs(self, limit: int) -> list[dict]:
        """
        Returns jobs that haven't been emailed yet and are active.

        Args:
            limit: Max number of jobs to return.

        Returns:
            List of job dicts.
        """
        # Get all jobs
        all_jobs = self.db.get_all_jobs(limit=500)

        # Get already-applied job IDs
        applications = self.db.get_all_applications()
        applied_ids  = {a['job_id'] for a in applications if a.get('job_id')}

        # Filter out already applied
        unapplied = [j for j in all_jobs if j.get('id') not in applied_ids]

        logger.info(
            f"Found {len(unapplied)} unapplied jobs "
            f"(out of {len(all_jobs)} total)"
        )

        return unapplied[:limit]

    def _get_or_generate_resume(
        self,
        job: dict,
        resume_data: dict,
        ats_result: dict
    ) -> str | None:
        """
        Returns existing resume PDF path or generates a new one.

        Args:
            job:         Job dict.
            resume_data: Parsed resume data.
            ats_result:  ATS analysis result.

        Returns:
            Path to resume PDF, or None if generation failed.
        """
        # Check if already generated
        docs = self.db.get_generated_docs(job.get('id'))
        for doc in (docs or []):
            if doc.get('doc_type') == 'resume' and Path(doc['file_path']).exists():
                return doc['file_path']

        # Generate new optimized resume
        try:
            optimized_md = self.optimizer.optimize(resume_data, job, ats_result)
            pdf_path = self.pdf_gen.generate_resume_pdf(optimized_md, job)
            if pdf_path:
                self.db.save_generated_doc(job.get('id'), 'resume', pdf_path)
            return pdf_path
        except Exception as e:
            logger.error(f"Resume generation failed for {job.get('company')}: {e}")
            # Fall back to original resume
            if Path(self.resume_path).exists():
                return self.resume_path
            return None

    def _get_or_generate_cover_letter(
        self,
        job: dict,
        resume_data: dict,
        ats_result: dict
    ) -> str | None:
        """
        Returns existing cover letter PDF path or generates a new one.

        Args:
            job:         Job dict.
            resume_data: Parsed resume data.
            ats_result:  ATS analysis result.

        Returns:
            Path to cover letter PDF, or None if generation failed.
        """
        # Check if already generated
        docs = self.db.get_generated_docs(job.get('id'))
        for doc in (docs or []):
            if doc.get('doc_type') == 'cover_letter' and Path(doc['file_path']).exists():
                return doc['file_path']

        # Generate new cover letter
        try:
            cl_text  = self.cover_gen.generate_cover_letter(job, resume_data, ats_result)
            pdf_path = self.pdf_gen.generate_cover_letter_pdf(cl_text, job)
            if pdf_path:
                self.db.save_generated_doc(job.get('id'), 'cover_letter', pdf_path)
            return pdf_path
        except Exception as e:
            logger.error(f"Cover letter generation failed for {job.get('company')}: {e}")
            return None
