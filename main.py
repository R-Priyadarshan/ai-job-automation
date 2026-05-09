"""
============================================================
main.py — Full Workflow Orchestrator
------------------------------------------------------------
PURPOSE:
    The main entry point for the AI Job Application System.
    Ties together ALL components into one complete workflow.

FULL WORKFLOW (runs in sequence):
    1. Load configuration
    2. Check Ollama is running
    3. Scrape new jobs from all sources
    4. For each new job:
        a. Parse your resume
        b. Run ATS matching
        c. If score >= threshold:
            - Optimize resume for this job
            - Generate cover letter
            - Generate both PDFs
            - Draft recruiter email
            - Save everything to database
    5. Send Telegram summary notification

USAGE:
    # Run full pipeline
    python main.py

    # Run only scraping
    python main.py --scrape-only

    # Run only AI analysis on existing jobs
    python main.py --analyze-only

    # Run for a specific job ID
    python main.py --job-id 42

    # Test a specific scraper
    python main.py --test-scraper remoteok
============================================================
"""

import sys                           # System operations
import argparse                      # Command-line argument parsing
from pathlib import Path             # File paths
from loguru import logger            # Beautiful logging
from rich.console import Console     # Rich terminal output
from rich.table import Table         # Rich tables
from rich.progress import Progress, SpinnerColumn, TextColumn  # Progress bars
from rich import print as rprint     # Colored print

# Add project root to Python path so imports work correctly
sys.path.insert(0, str(Path(__file__).parent))

# Import all our modules
from src.utils.config_loader import load_config
from src.database.db_manager import DatabaseManager
from src.scrapers.scraper_manager import ScraperManager
from src.ai_engine.ollama_client import OllamaClient
from src.ai_engine.resume_parser import ResumeParser
from src.ai_engine.ats_matcher import ATSMatcher
from src.ai_engine.resume_optimizer import ResumeOptimizer
from src.ai_engine.cover_letter_generator import CoverLetterGenerator
from src.generators.pdf_generator import PDFGenerator
from src.utils.notifier import TelegramNotifier


# Create Rich console for beautiful output
console = Console()


def setup_logging(config: dict):
    """
    Configures the Loguru logger.
    Logs go to both console and a rotating log file.

    Args:
        config: Config dict with logging settings.
    """
    log_cfg = config.get('logging', {})
    log_file = log_cfg.get('log_file', 'logs/app.log')
    log_level = log_cfg.get('level', 'INFO')

    # Create log directory if needed
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    # Remove default handler and add our custom ones
    logger.remove()

    # Console handler — colored, readable
    logger.add(
        sys.stdout,
        level=log_level,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>",
        colorize=True,
    )

    # File handler — detailed, rotates at 10MB
    logger.add(
        log_file,
        level="DEBUG",                           # Always log debug to file
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {module}:{line} | {message}",
        rotation="10 MB",                        # Rotate when file hits 10MB
        retention="7 days",                      # Keep logs for 7 days
        compression="zip",                       # Compress old logs
    )


def check_prerequisites(config: dict) -> bool:
    """
    Checks that all required services and files are in place
    before running the main workflow.

    Args:
        config: Config dict.

    Returns:
        True if all checks pass, False otherwise.
    """
    all_ok = True

    console.print("\n[bold blue]🔍 Checking Prerequisites...[/bold blue]")

    # 1. Check Ollama is running
    ai_client = OllamaClient(config)
    if ai_client.is_available():
        models = ai_client.list_models()
        model_name = config['ollama']['model']

        console.print(f"[green]✅ Ollama is running[/green]")
        console.print(f"[green]   Available models: {', '.join(models) or 'none'}[/green]")

        # Check if the configured model is installed
        if not any(model_name in m for m in models):
            console.print(
                f"[yellow]⚠️  Model '{model_name}' not found![/yellow]\n"
                f"[yellow]   Run: ollama pull {model_name}[/yellow]"
            )
            all_ok = False
    else:
        console.print(
            "[red]❌ Ollama is NOT running![/red]\n"
            "[red]   Start it with: ollama serve[/red]\n"
            "[red]   Then download a model: ollama pull qwen2.5[/red]"
        )
        all_ok = False

    # 2. Check resume file exists
    resume_path = config['user']['resume_path']
    if Path(resume_path).exists():
        console.print(f"[green]✅ Resume found: {resume_path}[/green]")
    else:
        console.print(
            f"[red]❌ Resume not found: {resume_path}[/red]\n"
            f"[red]   Create a resume text file at that path[/red]"
        )
        all_ok = False

    # 3. Check output directories
    Path("data/pdfs").mkdir(parents=True, exist_ok=True)
    Path("logs").mkdir(parents=True, exist_ok=True)
    console.print("[green]✅ Output directories ready[/green]")

    return all_ok


def run_scraping(config: dict) -> list[dict]:
    """
    Runs all job scrapers and returns new jobs.

    Args:
        config: Config dict.

    Returns:
        List of all jobs found (new + existing from db).
    """
    console.print("\n[bold blue]🕷️ Starting Job Scraping...[/bold blue]")

    manager = ScraperManager(config)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        task = progress.add_task("Scraping jobs from all sources...", total=None)
        jobs = manager.run_all()
        progress.update(task, completed=True)

    console.print(f"[green]✅ Scraped {len(jobs)} jobs total[/green]")
    return jobs


def run_ai_analysis(config: dict, jobs: list[dict] = None):
    """
    Runs AI analysis on jobs that haven't been analyzed yet.

    For each qualifying job:
    1. Calculate ATS score
    2. If score >= threshold: generate documents

    Args:
        config: Config dict.
        jobs: Optional list of jobs to analyze. If None, fetches from DB.
    """
    console.print("\n[bold blue]🤖 Running AI Analysis...[/bold blue]")

    # Initialize components
    db = DatabaseManager(config['database']['path'])
    parser = ResumeParser()
    ats = ATSMatcher(config)
    optimizer = ResumeOptimizer(config)
    cover_gen = CoverLetterGenerator(config)
    pdf_gen = PDFGenerator(config)
    notifier = TelegramNotifier(config)

    # Parse user's resume ONCE (reuse for all jobs)
    resume_path = config['user']['resume_path']
    console.print(f"[blue]📄 Parsing your resume: {resume_path}[/blue]")
    resume_data = parser.parse(resume_path)

    if not resume_data['full_text']:
        console.print("[red]❌ Resume is empty! Check the file path in config.yaml[/red]")
        return

    console.print(f"[green]✅ Resume parsed — {len(resume_data['skills'])} skills found[/green]")

    # Get unapplied jobs from database (or use provided list)
    if jobs is None:
        jobs_to_analyze = db.get_unapplied_jobs()
    else:
        jobs_to_analyze = jobs

    if not jobs_to_analyze:
        console.print("[yellow]ℹ️ No new jobs to analyze[/yellow]")
        return

    console.print(f"[blue]🔍 Analyzing {len(jobs_to_analyze)} jobs...[/blue]\n")

    min_score = config['ats']['minimum_score']
    processed = 0
    applied = 0

    # Create summary table for results
    table = Table(title="Job Analysis Results", show_header=True, header_style="bold blue")
    table.add_column("Title", style="cyan", max_width=30)
    table.add_column("Company", style="green", max_width=20)
    table.add_column("ATS Score", justify="center")
    table.add_column("Status", justify="center")

    for job in jobs_to_analyze:
        processed += 1
        job_id = job.get('id')

        # Check if already analyzed
        existing_score = db.get_ats_score(job_id)
        if existing_score:
            logger.debug(f"Job {job_id} already analyzed, skipping")
            continue

        logger.info(f"[{processed}/{len(jobs_to_analyze)}] Analyzing: {job.get('title')}")

        # ---- STEP 1: ATS Matching ----
        ats_result = ats.analyze(job, resume_data)
        score = ats_result['score']

        # Save ATS results to database
        db.save_ats_score({
            'job_id':           job_id,
            'score':            score,
            'matching_skills':  ', '.join(ats_result.get('matching_skills', [])),
            'missing_skills':   ', '.join(ats_result.get('missing_skills', [])),
            'analysis_text':    ats_result.get('analysis_text', ''),
        })

        score_label = ats.get_score_label(score)

        # Determine if we should generate documents
        if score >= min_score:
            status = f"[green]✅ Applying ({score}/100)[/green]"

            # ---- STEP 2: Optimize Resume ----
            logger.info(f"Optimizing resume for: {job.get('title')}")
            optimized_resume_md = optimizer.optimize(resume_data, job, ats_result)

            # ---- STEP 3: Generate Cover Letter ----
            logger.info(f"Generating cover letter for: {job.get('title')}")
            cover_letter_text = cover_gen.generate_cover_letter(job, resume_data, ats_result)

            # ---- STEP 4: Generate Recruiter Email ----
            email_draft = cover_gen.generate_recruiter_email(job, resume_data)

            # ---- STEP 5: Create PDFs ----
            resume_pdf = pdf_gen.generate_resume_pdf(optimized_resume_md, job)
            cover_pdf = pdf_gen.generate_cover_letter_pdf(cover_letter_text, job)

            # Save generated doc paths
            if resume_pdf:
                db.save_generated_doc(job_id, 'resume', resume_pdf)
            if cover_pdf:
                db.save_generated_doc(job_id, 'cover_letter', cover_pdf)

            # ---- STEP 6: Record Application ----
            db.record_application({
                'job_id':             job_id,
                'ats_score':          score,
                'notes':              score_label,
                'resume_path':        resume_pdf,
                'cover_letter_path':  cover_pdf,
                'email_draft':        email_draft,
            })

            # Send notification for high matches
            if score >= config['ats']['high_match_threshold']:
                notifier.notify_high_match(job, score)

            applied += 1
        else:
            status = f"[yellow]⏭️ Skipped ({score}/100)[/yellow]"

        # Add to results table
        table.add_row(
            job.get('title', '')[:30],
            job.get('company', '')[:20],
            f"{score}/100",
            status,
        )

    # Display results table
    console.print(table)
    console.print(
        f"\n[green]✅ Analysis Complete![/green]\n"
        f"   Analyzed: {processed} jobs\n"
        f"   Documents generated: {applied} jobs\n"
    )

    # Daily summary notification
    stats = db.get_statistics()
    notifier.notify_daily_summary(stats)


def show_stats(config: dict):
    """
    Displays current database statistics in the terminal.

    Args:
        config: Config dict.
    """
    db = DatabaseManager(config['database']['path'])
    stats = db.get_statistics()

    console.print("\n[bold blue]📊 Database Statistics[/bold blue]")

    table = Table(show_header=False)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total Jobs Scraped", str(stats.get('total_jobs', 0)))
    table.add_row("Total Applications", str(stats.get('total_applications', 0)))
    table.add_row("Average ATS Score", f"{stats.get('avg_ats_score', 0)}/100")

    if stats.get('jobs_by_source'):
        for source, count in stats['jobs_by_source'].items():
            table.add_row(f"  — {source}", str(count))

    console.print(table)


def main():
    """
    Main function — parses arguments and runs the selected workflow.
    """
    # ---- Argument Parser ----
    # Allows users to run specific parts of the system
    parser = argparse.ArgumentParser(
        description="AI Job Application Automation System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    # Run full pipeline
  python main.py --scrape-only      # Only scrape jobs
  python main.py --analyze-only     # Only run AI analysis
  python main.py --stats            # Show statistics
  python main.py --job-id 42        # Analyze specific job
  python main.py --test-scraper remoteok  # Test one scraper
        """
    )

    parser.add_argument('--scrape-only', action='store_true',
                        help='Only run the job scrapers, skip AI analysis')
    parser.add_argument('--analyze-only', action='store_true',
                        help='Only run AI analysis on existing jobs in DB')
    parser.add_argument('--stats', action='store_true',
                        help='Show database statistics and exit')
    parser.add_argument('--job-id', type=int,
                        help='Run AI analysis on a specific job ID')
    parser.add_argument('--test-scraper', type=str,
                        help='Test a specific scraper: remoteok, linkedin, etc.')
    parser.add_argument('--config', type=str, default='config.yaml',
                        help='Path to config file (default: config.yaml)')

    args = parser.parse_args()

    # ---- Print Banner ----
    console.print("""
[bold blue]
╔═══════════════════════════════════════════════════╗
║     🤖 AI JOB APPLICATION AUTOMATION SYSTEM       ║
║     100% Local • Zero Cost • Powered by Ollama    ║
╚═══════════════════════════════════════════════════╝
[/bold blue]""")

    # ---- Load Configuration ----
    try:
        config = load_config(args.config)
        console.print(f"[green]✅ Config loaded from: {args.config}[/green]")
    except FileNotFoundError as e:
        console.print(f"[red]❌ {e}[/red]")
        sys.exit(1)

    # ---- Setup Logging ----
    setup_logging(config)

    # ---- Handle --stats flag ----
    if args.stats:
        show_stats(config)
        return

    # ---- Handle --test-scraper flag ----
    if args.test_scraper:
        console.print(f"\n[blue]Testing scraper: {args.test_scraper}[/blue]")
        manager = ScraperManager(config)
        jobs = manager.run_single(args.test_scraper)
        console.print(f"[green]Found {len(jobs)} jobs[/green]")
        for job in jobs[:5]:
            console.print(f"  • {job['title']} @ {job['company']}")
        return

    # ---- Check Prerequisites ----
    if not args.scrape_only:  # Skip Ollama check if only scraping
        ready = check_prerequisites(config)
        if not ready:
            console.print(
                "\n[yellow]⚠️  Prerequisites not met. "
                "Fix the issues above, then run again.[/yellow]"
            )
            # Continue with scraping even if AI check fails
            if not args.analyze_only:
                run_scraping(config)
            return

    # ---- Handle --job-id flag ----
    if args.job_id:
        db = DatabaseManager(config['database']['path'])
        job = db.get_job_by_id(args.job_id)
        if not job:
            console.print(f"[red]❌ Job ID {args.job_id} not found in database[/red]")
            return
        run_ai_analysis(config, [job])
        return

    # ---- Full Pipeline or Partial ----
    if args.scrape_only:
        # Only scrape, save to DB, no AI
        run_scraping(config)

    elif args.analyze_only:
        # Only AI analysis on existing DB jobs
        run_ai_analysis(config)

    else:
        # Full pipeline: scrape + analyze
        run_scraping(config)
        run_ai_analysis(config)

    # ---- Final Stats ----
    show_stats(config)
    console.print("\n[bold green]🎉 Pipeline Complete! Check data/pdfs/ for generated documents.[/bold green]")
    console.print("[blue]💡 Run 'streamlit run dashboard/app.py' to open the dashboard[/blue]\n")


# Python entry point
# Only runs when this file is executed directly
# Not when it's imported as a module
if __name__ == "__main__":
    main()
