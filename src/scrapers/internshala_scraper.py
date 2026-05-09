"""
============================================================
src/scrapers/internshala_scraper.py
------------------------------------------------------------
PURPOSE:
    Scrapes internship and fresher job listings from
    Internshala (internshala.com)

APPROACH:
    Internshala is a regular HTML website, so we use:
    1. requests — to fetch the HTML
    2. BeautifulSoup — to parse and extract data from HTML

    We target their public search pages which are accessible
    without login for basic listings.

TARGET CATEGORIES:
    - Machine Learning internships
    - Software Development
    - AI/Data Science
    - Embedded Systems

IMPORTANT NOTE:
    Internshala may update their HTML structure. If this scraper
    breaks, check the CSS selectors in the _parse_jobs() method.
    Use browser DevTools (F12) to find the new selectors.
============================================================
"""

import re                            # Regular expressions
from loguru import logger            # Logging
from bs4 import BeautifulSoup        # HTML parsing
from .base_scraper import BaseScraper


class IntershalaScraper(BaseScraper):
    """
    Scrapes internship listings from Internshala.
    Focuses on tech internships in AI, ML, and software.
    """

    # Base URL for Internshala search
    BASE_URL = "https://internshala.com"

    # Search categories relevant to tech/AI
    SEARCH_CATEGORIES = [
        "machine-learning",
        "python",
        "artificial-intelligence",
        "data-science",
        "software-development",
        "embedded-systems",
    ]

    def scrape(self) -> list[dict]:
        """
        Scrapes internships from multiple Internshala categories.

        Returns:
            List of normalized job dictionaries.
        """
        logger.info("Starting Internshala scraping...")

        all_jobs = []
        seen_urls = set()

        for category in self.SEARCH_CATEGORIES:
            # Internshala URL format for category search
            url = f"{self.BASE_URL}/internships/{category}-internship"

            logger.debug(f"Scraping Internshala: {category}")
            self._polite_delay()

            response = self._safe_get(url)
            if not response:
                logger.warning(f"Failed to fetch Internshala: {url}")
                continue

            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')

            # Parse job listings from the HTML
            jobs = self._parse_jobs(soup, category)

            for job in jobs:
                if job['url'] not in seen_urls:
                    seen_urls.add(job['url'])
                    all_jobs.append(job)

            if len(all_jobs) >= self.max_jobs:
                break

        logger.info(f"Internshala: Found {len(all_jobs)} listings")
        return all_jobs[:self.max_jobs]

    def _parse_jobs(self, soup: BeautifulSoup, category: str) -> list[dict]:
        """
        Extracts job listings from Internshala's HTML structure.

        Internshala's HTML structure (as of 2024):
        Each listing is inside a <div class="individual_internship">
        Inside that:
        - .job-internship-name = Job title
        - .company-name = Company name
        - .location-names-container = Location
        - .internship-other-details-container = Stipend, Duration etc.

        Args:
            soup: Parsed HTML content.
            category: Current category being scraped.

        Returns:
            List of job dicts extracted from this page.
        """
        jobs = []

        # Find all internship listing containers
        # Internshala uses this class for each listing card
        listings = soup.find_all('div', class_='individual_internship')

        if not listings:
            # Try alternative selector (Internshala sometimes updates HTML)
            listings = soup.find_all('div', attrs={'data-internship_id': True})

        if not listings:
            logger.warning(f"Internshala: No listings found for {category}. HTML structure may have changed.")
            return []

        for listing in listings:
            try:
                job = self._extract_listing_data(listing, category)
                if job:
                    jobs.append(job)
            except Exception as e:
                logger.debug(f"Error parsing Internshala listing: {e}")
                continue

        return jobs

    def _extract_listing_data(self, listing, category: str) -> dict | None:
        """
        Extracts data from a single Internshala listing card.

        Args:
            listing: BeautifulSoup element for one job card.
            category: Job category (used as tag).

        Returns:
            Job dictionary or None if extraction failed.
        """
        # Extract job title
        title_el = listing.find(class_=['job-internship-name', 'profile'])
        if not title_el:
            # Try heading tags
            title_el = listing.find(['h3', 'h4', 'a'])
        title = title_el.get_text(strip=True) if title_el else 'Unknown Title'

        # Extract company name
        company_el = listing.find(class_='company-name')
        if not company_el:
            company_el = listing.find('a', class_='link_display_like_text')
        company = company_el.get_text(strip=True) if company_el else 'Unknown Company'

        # Extract location
        location_el = listing.find(class_=['location-names-container', 'locations-label'])
        location = location_el.get_text(strip=True) if location_el else 'India'
        if not location:
            location = 'India'

        # Extract the link to the full listing
        link_el = listing.find('a', href=True)
        if link_el:
            href = link_el['href']
            # Make it absolute URL if it's relative
            url = href if href.startswith('http') else f"{self.BASE_URL}{href}"
        else:
            return None  # Skip listings without links

        # Extract stipend/salary
        stipend_el = listing.find(class_=['stipend', 'stipend_content'])
        salary = stipend_el.get_text(strip=True) if stipend_el else 'Unpaid/Not specified'

        # Extract duration (internship-specific)
        duration_el = listing.find(class_=['duration-label', 'item_body'])
        duration = duration_el.get_text(strip=True) if duration_el else ''

        # Build description from available info
        description = f"Category: {category}. "
        if duration:
            description += f"Duration: {duration}. "
        description += f"Location: {location}."

        return self._normalize_job({
            'title':        title,
            'company':      company,
            'location':     location,
            'url':          url,
            'source':       'internshala',
            'description':  description,
            'skills':       category.replace('-', ', '),
            'salary':       salary,
            'job_type':     'Internship',
            'posted_date':  '',
        })
