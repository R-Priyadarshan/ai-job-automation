"""
============================================================
src/scrapers/remoteok_scraper.py
------------------------------------------------------------
PURPOSE:
    Scrapes job listings from RemoteOK (https://remoteok.com)

WHY REMOTEOK IS EASY TO SCRAPE:
    RemoteOK provides a PUBLIC JSON API endpoint at:
    https://remoteok.com/api
    This returns all jobs as JSON — no HTML parsing needed!
    This is the most beginner-friendly scraper.

HOW IT WORKS:
    1. Call the RemoteOK JSON API
    2. Parse the JSON response
    3. Filter jobs matching our keywords
    4. Return standardized list of job dictionaries

RATE LIMITS:
    RemoteOK's ToS allows scraping with proper delays.
    We wait between requests to be respectful.
============================================================
"""

import json                          # Parse JSON responses
from datetime import datetime        # Date formatting
from loguru import logger            # Logging
from .base_scraper import BaseScraper  # Our base class


class RemoteOKScraper(BaseScraper):
    """
    Scrapes job listings from RemoteOK's public JSON API.

    RemoteOK provides a free public API, so this is perfectly
    legal and doesn't require any authentication.
    """

    # RemoteOK's public API endpoint — returns all jobs as JSON
    API_URL = "https://remoteok.com/api"

    def scrape(self) -> list[dict]:
        """
        Fetches and filters jobs from RemoteOK API.

        Returns:
            List of normalized job dictionaries.
        """
        logger.info("Starting RemoteOK scraping...")

        # Politely wait before making request
        self._polite_delay()

        # Fetch the JSON API
        # RemoteOK requires a specific User-Agent or it returns 403
        response = self.session.get(
            self.API_URL,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; JobBot/1.0)",
                "Accept": "application/json",
            },
            timeout=30
        )

        # Check if request succeeded
        if not response or response.status_code != 200:
            logger.error(f"RemoteOK API failed: {response.status_code if response else 'No response'}")
            return []

        # Parse JSON response
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse RemoteOK JSON: {e}")
            return []

        # RemoteOK returns a list; first item is metadata, skip it
        # The rest are job listings
        if not isinstance(data, list) or len(data) < 2:
            logger.warning("RemoteOK returned unexpected data format.")
            return []

        # Skip the first element (it's legal/metadata info)
        raw_jobs = data[1:]

        logger.info(f"RemoteOK returned {len(raw_jobs)} total jobs")

        # Filter and convert jobs
        filtered_jobs = []
        for raw_job in raw_jobs:

            # Skip if not a proper job dict
            if not isinstance(raw_job, dict):
                continue

            # Get job details
            title = raw_job.get('position', '')
            company = raw_job.get('company', '')
            description = raw_job.get('description', '')
            tags = raw_job.get('tags', [])  # Skills/tags list

            # Convert tags list to comma-separated string
            skills_str = ', '.join(tags) if tags else ''

            # Check if this job matches our keywords
            # We search in title, description, AND tags
            search_text = f"{title} {description} {skills_str}".lower()

            if not self._matches_keywords(search_text):
                continue  # Skip irrelevant jobs

            # Parse the date (RemoteOK uses ISO 8601 format)
            posted_date = raw_job.get('date', '')
            if posted_date:
                try:
                    # Convert ISO datetime to simple date string
                    dt = datetime.fromisoformat(posted_date.replace('Z', '+00:00'))
                    posted_date = dt.strftime('%Y-%m-%d')
                except Exception:
                    posted_date = posted_date[:10]  # Just take first 10 chars

            # Build normalized job dict
            job = self._normalize_job({
                'title':        title,
                'company':      company,
                'location':     'Remote',          # RemoteOK is all remote
                'url':          f"https://remoteok.com{raw_job.get('url', '')}",
                'source':       'remoteok',
                'description':  self._clean_html(description),
                'skills':       skills_str,
                'salary':       raw_job.get('salary', 'Not specified'),
                'job_type':     'Remote Full-time',
                'posted_date':  posted_date,
            })

            # Only add jobs with a valid URL
            if job['url'] and job['url'] != 'https://remoteok.com':
                filtered_jobs.append(job)

            # Stop after reaching max jobs limit
            if len(filtered_jobs) >= self.max_jobs:
                break

        logger.info(f"RemoteOK: Found {len(filtered_jobs)} matching jobs")
        return filtered_jobs

    def _matches_keywords(self, text: str) -> bool:
        """
        Checks if the given text contains any of our target keywords.

        Args:
            text: Lowercased job text to search in.

        Returns:
            True if at least one keyword is found.
        """
        for keyword in self.keywords:
            if keyword.lower() in text:
                return True
        return False

    def _clean_html(self, html_text: str) -> str:
        """
        Removes HTML tags from job descriptions.
        RemoteOK descriptions sometimes contain HTML markup.

        Args:
            html_text: Text possibly containing HTML tags.

        Returns:
            Clean plain text string.
        """
        if not html_text:
            return ''

        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_text, 'html.parser')
            return soup.get_text(separator=' ', strip=True)
        except Exception:
            # If BeautifulSoup fails, do basic tag removal
            import re
            clean = re.sub(r'<[^>]+>', ' ', html_text)
            return ' '.join(clean.split())
