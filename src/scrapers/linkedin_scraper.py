"""
============================================================
src/scrapers/linkedin_scraper.py
------------------------------------------------------------
PURPOSE:
    Safely scrapes job listings from LinkedIn Jobs.

IMPORTANT — LINKEDIN SCRAPING POLICY:
    LinkedIn's ToS prohibits automated scraping of user data.
    However, PUBLIC job listings pages are different.

    We use ONLY:
    ✅ Public job search pages (no login required)
    ✅ Appropriate delays between requests
    ✅ Rotating user agents
    ✅ We do NOT scrape profiles or private data
    ✅ We do NOT bypass any login walls

    This is similar to how Google indexes LinkedIn pages.

APPROACH:
    LinkedIn's public job search URL:
    https://www.linkedin.com/jobs/search/?keywords=KEYWORD&location=LOCATION

    We use BeautifulSoup to parse the public HTML.
    NOTE: LinkedIn frequently updates their HTML, so
    selectors may need updates. Check and update selectors
    if scraping stops working.

ALTERNATIVE (if LinkedIn blocks):
    Use LinkedIn's official Job Search API (free tier available)
    at: https://developer.linkedin.com/
============================================================
"""

import re                            # Regex for text cleaning
import time                          # Delays
from urllib.parse import urlencode   # URL encoding
from loguru import logger            # Logging
from bs4 import BeautifulSoup        # HTML parsing
from .base_scraper import BaseScraper


class LinkedInScraper(BaseScraper):
    """
    Safely scrapes public LinkedIn job listings.

    Implements all safety measures to be respectful:
    - Random delays between requests
    - Rotating user agents
    - Only accessing public pages
    - No authentication bypass
    """

    BASE_SEARCH_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"

    # LinkedIn's public job listing page (no login needed)
    PUBLIC_SEARCH_URL = "https://www.linkedin.com/jobs/search/"

    def scrape(self) -> list[dict]:
        """
        Scrapes LinkedIn public job listings.

        LinkedIn is more aggressive about blocking scrapers,
        so we implement extra safety measures and gracefully
        fall back if blocked.

        Returns:
            List of normalized job dictionaries.
        """
        logger.info("Starting LinkedIn scraping (safe mode)...")

        all_jobs = []
        seen_urls = set()

        # Search for each keyword separately
        for keyword in self.keywords[:5]:  # Limit to 5 keywords to avoid blocks

            self._polite_delay()
            self._polite_delay()  # Extra delay for LinkedIn

            jobs = self._search_keyword(keyword)

            for job in jobs:
                if job['url'] not in seen_urls:
                    seen_urls.add(job['url'])
                    all_jobs.append(job)

            if len(all_jobs) >= self.max_jobs:
                break

        logger.info(f"LinkedIn: Found {len(all_jobs)} jobs")
        return all_jobs[:self.max_jobs]

    def _search_keyword(self, keyword: str) -> list[dict]:
        """
        Searches LinkedIn for a specific keyword.

        Args:
            keyword: Job search keyword.

        Returns:
            List of job dicts from this search.
        """
        # Build the LinkedIn search URL with query parameters
        params = {
            'keywords': keyword,
            'location': 'Worldwide',
            'f_WT': '2',      # Remote work filter (2 = remote)
            'f_TPR': 'r86400',  # Posted in last 24 hours
            'start': '0',
        }

        # Encode parameters into URL query string
        search_url = f"{self.PUBLIC_SEARCH_URL}?{urlencode(params)}"

        logger.debug(f"LinkedIn search: {keyword}")

        response = self._safe_get(search_url)
        if not response:
            logger.warning(f"LinkedIn blocked or failed for keyword: {keyword}")
            return []

        # Check if we hit a login wall or CAPTCHA
        if 'authwall' in response.url or 'checkpoint' in response.url:
            logger.warning("LinkedIn requires login — using fallback approach")
            return self._fallback_scrape(keyword)

        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        return self._parse_job_cards(soup, keyword)

    def _parse_job_cards(self, soup: BeautifulSoup, keyword: str) -> list[dict]:
        """
        Extracts job data from LinkedIn's HTML job cards.

        LinkedIn job card structure (public pages):
        <div class="job-search-card">
            <h3 class="base-search-card__title">Job Title</h3>
            <h4 class="base-search-card__subtitle">Company</h4>
            <span class="job-search-card__location">Location</span>
            <a class="base-card__full-link">Link to job</a>
        </div>

        Args:
            soup: Parsed HTML page.
            keyword: The keyword that was searched.

        Returns:
            List of job dictionaries.
        """
        jobs = []

        # Try multiple selectors (LinkedIn changes their HTML structure often)
        job_cards = soup.find_all('div', class_='job-search-card')
        if not job_cards:
            job_cards = soup.find_all('li', class_='jobs-search__results-list')
        if not job_cards:
            job_cards = soup.find_all('div', class_='base-card')

        if not job_cards:
            logger.warning("LinkedIn: No job cards found. Structure may have changed.")
            return []

        for card in job_cards:
            try:
                # Extract title
                title_el = card.find(class_=['base-search-card__title', 'job-result-card__title'])
                title = title_el.get_text(strip=True) if title_el else None
                if not title:
                    continue

                # Extract company
                company_el = card.find(class_=['base-search-card__subtitle', 'job-result-card__subtitle'])
                company = company_el.get_text(strip=True) if company_el else 'Unknown Company'

                # Extract location
                location_el = card.find(class_=['job-search-card__location', 'job-result-card__location'])
                location = location_el.get_text(strip=True) if location_el else 'Not specified'

                # Extract job URL
                link_el = card.find('a', class_='base-card__full-link')
                if not link_el:
                    link_el = card.find('a', href=True)
                url = link_el['href'] if link_el else None

                if not url:
                    continue

                # Clean URL — remove tracking parameters
                url = url.split('?')[0]

                # Extract posted date if available
                time_el = card.find('time')
                posted_date = time_el.get('datetime', '') if time_el else ''

                # Build job dict
                job = self._normalize_job({
                    'title':        title,
                    'company':      company,
                    'location':     location,
                    'url':          url,
                    'source':       'linkedin',
                    'description':  f"LinkedIn job for keyword: {keyword}. Visit URL for full description.",
                    'skills':       keyword,
                    'salary':       'Not specified',
                    'job_type':     'Full-time',
                    'posted_date':  posted_date,
                })

                jobs.append(job)

            except Exception as e:
                logger.debug(f"Error parsing LinkedIn card: {e}")
                continue

        return jobs

    def _fallback_scrape(self, keyword: str) -> list[dict]:
        """
        Fallback method using LinkedIn's public RSS-like feed.
        Used when the main scraping is blocked.

        Args:
            keyword: Job keyword to search.

        Returns:
            List of job dicts (may be empty if all methods fail).
        """
        logger.info(f"LinkedIn fallback: trying alternative for '{keyword}'")

        # LinkedIn provides some data through their jobs API for public access
        fallback_url = (
            f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
            f"?keywords={keyword.replace(' ', '%20')}&location=Worldwide&start=0"
        )

        response = self._safe_get(fallback_url)
        if not response:
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        return self._parse_job_cards(soup, keyword)
