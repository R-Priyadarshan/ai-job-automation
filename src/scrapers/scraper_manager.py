"""
============================================================
src/scrapers/scraper_manager.py
------------------------------------------------------------
PURPOSE:
    Orchestrates all scrapers — runs them all and combines
    the results into a single list of jobs.

    Also handles:
    - Deduplication across all scrapers
    - Saving all results to the database
    - Error handling if one scraper fails

DESIGN PATTERN:
    This is the "Façade" pattern:
    - Other code only needs to call ScraperManager.run_all()
    - It doesn't need to know about individual scrapers
    - Adding a new scraper = just add it to the list here
============================================================
"""

from loguru import logger
from .remoteok_scraper import RemoteOKScraper
from .weworkremotely_scraper import WeWorkRemotelyScraper
from .internshala_scraper import IntershalaScraper
from .linkedin_scraper import LinkedInScraper
from src.database.db_manager import DatabaseManager


class ScraperManager:
    """
    Runs all job scrapers and saves results to database.

    Usage:
        manager = ScraperManager(config)
        jobs = manager.run_all()
        print(f"Found {len(jobs)} new jobs")
    """

    def __init__(self, config: dict):
        """
        Initialize all scrapers.

        Args:
            config: Configuration dictionary from config.yaml
        """
        self.config = config
        self.db = DatabaseManager(config['database']['path'])

        # Initialize all scrapers
        # Each scraper receives the same config dict
        self.scrapers = [
            RemoteOKScraper(config),
            WeWorkRemotelyScraper(config),
            IntershalaScraper(config),
            LinkedInScraper(config),
        ]

        logger.info(f"ScraperManager initialized with {len(self.scrapers)} scrapers")

    def run_all(self) -> list[dict]:
        """
        Runs ALL scrapers and saves unique jobs to database.

        Flow:
        1. Run each scraper
        2. Combine all results
        3. Deduplicate by URL
        4. Save new jobs to database
        5. Return list of new jobs

        Returns:
            List of newly inserted job dictionaries.
        """
        all_jobs = []
        seen_urls = set()     # Track URLs to deduplicate across scrapers
        scraper_stats = {}    # Track how many jobs each scraper found

        logger.info("=" * 50)
        logger.info("Starting all scrapers...")
        logger.info("=" * 50)

        for scraper in self.scrapers:
            scraper_name = scraper.__class__.__name__

            try:
                logger.info(f"Running: {scraper_name}")

                # Run the scraper — get its job list
                jobs = scraper.scrape()

                # Track stats for this scraper
                scraper_stats[scraper_name] = len(jobs)

                # Add unique jobs to combined list
                new_from_this_scraper = 0
                for job in jobs:
                    url = job.get('url', '')
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_jobs.append(job)
                        new_from_this_scraper += 1

                logger.info(f"{scraper_name}: {new_from_this_scraper} unique jobs found")

            except Exception as e:
                # If one scraper fails, log the error but CONTINUE with others
                logger.error(f"{scraper_name} FAILED: {e}")
                scraper_stats[scraper_name] = 0
                continue

        logger.info(f"Total jobs collected: {len(all_jobs)}")

        # Save all jobs to database
        new_in_db = 0
        for job in all_jobs:
            job_id = self.db.insert_job(job)
            if job_id:  # insert_job returns None for duplicates
                new_in_db += 1

        logger.info(f"New jobs saved to database: {new_in_db}")
        logger.info(f"Scraper stats: {scraper_stats}")

        return all_jobs

    def run_single(self, scraper_name: str) -> list[dict]:
        """
        Runs only a specific scraper by name.
        Useful for testing individual scrapers.

        Args:
            scraper_name: e.g., 'remoteok', 'linkedin', 'weworkremotely'

        Returns:
            Jobs from that specific scraper.
        """
        name_map = {
            'remoteok':         RemoteOKScraper,
            'weworkremotely':   WeWorkRemotelyScraper,
            'internshala':      IntershalaScraper,
            'linkedin':         LinkedInScraper,
        }

        scraper_class = name_map.get(scraper_name.lower())
        if not scraper_class:
            logger.error(f"Unknown scraper: {scraper_name}")
            return []

        scraper = scraper_class(self.config)
        return scraper.scrape()
