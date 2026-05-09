"""
============================================================
src/scrapers/weworkremotely_scraper.py
------------------------------------------------------------
PURPOSE:
    Scrapes job listings from WeWorkRemotely (weworkremotely.com)

HOW IT WORKS:
    WeWorkRemotely provides an RSS feed (XML format) for each
    job category. We parse this RSS feed using BeautifulSoup.

    RSS feeds are publicly available and designed for reading
    by programs — perfectly legal to scrape.

    RSS Feed URLs:
    - Programming: https://weworkremotely.com/categories/remote-programming-jobs.rss
    - DevOps: https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss
    - Design: https://weworkremotely.com/categories/remote-design-jobs.rss

PARSING:
    RSS is XML format. Each <item> tag = one job listing.
    We extract title, company, link, date from each <item>.
============================================================
"""

from datetime import datetime        # Date parsing
from loguru import logger            # Logging
from bs4 import BeautifulSoup        # HTML/XML parsing
from .base_scraper import BaseScraper


class WeWorkRemotelyScraper(BaseScraper):
    """
    Scrapes jobs from WeWorkRemotely's RSS feeds.
    Focuses on programming, DevOps, and engineering categories.
    """

    # RSS feed URLs for different job categories
    RSS_FEEDS = {
        'programming':  'https://weworkremotely.com/categories/remote-programming-jobs.rss',
        'devops':       'https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss',
        'data_science': 'https://weworkremotely.com/remote-jobs/search.rss?term=machine+learning',
        'ai':           'https://weworkremotely.com/remote-jobs/search.rss?term=artificial+intelligence',
    }

    def scrape(self) -> list[dict]:
        """
        Fetches jobs from all WeWorkRemotely RSS categories.

        Returns:
            List of normalized job dictionaries.
        """
        logger.info("Starting WeWorkRemotely scraping...")

        all_jobs = []
        seen_urls = set()  # Track URLs to avoid duplicates within this scraper

        # Iterate through each RSS feed category
        for category, rss_url in self.RSS_FEEDS.items():

            logger.debug(f"Fetching WWR RSS: {category}")
            self._polite_delay()  # Be polite between requests

            # Fetch the RSS XML content
            response = self._safe_get(rss_url)
            if not response:
                logger.warning(f"Failed to fetch WWR RSS: {rss_url}")
                continue

            # Parse XML using BeautifulSoup with lxml parser
            # 'xml' or 'lxml-xml' parser handles XML properly
            try:
                soup = BeautifulSoup(response.content, 'xml')
            except Exception:
                # Fallback to html.parser if lxml not available
                soup = BeautifulSoup(response.content, 'html.parser')

            # Find all <item> tags — each is one job listing
            items = soup.find_all('item')

            if not items:
                logger.warning(f"No items found in WWR RSS for {category}")
                continue

            logger.debug(f"WWR {category}: Found {len(items)} items")

            # Parse each job item
            for item in items:

                # Extract data from RSS item tags
                # Each tag is accessed with .find() and .get_text()
                title_tag = item.find('title')
                link_tag = item.find('link')
                pubdate_tag = item.find('pubDate')
                description_tag = item.find('description')

                # Skip items with missing critical data
                if not title_tag or not link_tag:
                    continue

                # Get text content from tags
                raw_title = title_tag.get_text(strip=True)
                url = link_tag.get_text(strip=True)
                pub_date = pubdate_tag.get_text(strip=True) if pubdate_tag else ''
                description_html = description_tag.get_text(strip=True) if description_tag else ''

                # Parse the title — WWR format is often "Company: Job Title"
                # Example: "ACME Corp: Senior Python Developer"
                if ': ' in raw_title:
                    parts = raw_title.split(': ', 1)
                    company = parts[0].strip()
                    title = parts[1].strip()
                else:
                    company = 'WeWorkRemotely'
                    title = raw_title

                # Clean HTML from description
                clean_description = self._clean_description(description_html)

                # Check keyword match
                search_text = f"{title} {clean_description}".lower()
                if not self._matches_keywords(search_text):
                    continue

                # Skip duplicates
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                # Parse date string
                formatted_date = self._parse_date(pub_date)

                # Extract skills from title and description
                skills = self._extract_skills(f"{title} {clean_description}")

                # Build normalized job
                job = self._normalize_job({
                    'title':        title,
                    'company':      company,
                    'location':     'Remote',
                    'url':          url,
                    'source':       'weworkremotely',
                    'description':  clean_description[:2000],  # Limit length
                    'skills':       ', '.join(skills),
                    'salary':       'Not specified',
                    'job_type':     'Remote',
                    'posted_date':  formatted_date,
                })

                all_jobs.append(job)

                # Stop when we hit the max jobs limit
                if len(all_jobs) >= self.max_jobs:
                    break

            # Break outer loop too if limit reached
            if len(all_jobs) >= self.max_jobs:
                break

        logger.info(f"WeWorkRemotely: Found {len(all_jobs)} matching jobs")
        return all_jobs

    def _matches_keywords(self, text: str) -> bool:
        """Check if text contains any target keyword."""
        for keyword in self.keywords:
            if keyword.lower() in text:
                return True
        return False

    def _clean_description(self, html_text: str) -> str:
        """Remove HTML tags and clean up text."""
        if not html_text:
            return ''
        try:
            soup = BeautifulSoup(html_text, 'html.parser')
            return soup.get_text(separator=' ', strip=True)
        except Exception:
            import re
            return re.sub(r'<[^>]+>', ' ', html_text).strip()

    def _parse_date(self, date_str: str) -> str:
        """
        Parse RFC 2822 date format from RSS feeds.
        Example: "Mon, 01 Jan 2024 12:00:00 +0000"

        Returns:
            Date string in YYYY-MM-DD format.
        """
        if not date_str:
            return ''
        try:
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(date_str)
            return dt.strftime('%Y-%m-%d')
        except Exception:
            return date_str[:10] if len(date_str) >= 10 else date_str

    def _extract_skills(self, text: str) -> list[str]:
        """
        Extracts common tech skills from text using keyword matching.
        This is a simple pattern-matching approach (no AI needed here).

        Args:
            text: Job title + description text.

        Returns:
            List of found skill names.
        """
        # Common technical skills to look for
        skill_patterns = [
            'Python', 'JavaScript', 'TypeScript', 'Java', 'C++', 'C#', 'Go', 'Rust',
            'React', 'Vue', 'Angular', 'Node.js', 'Django', 'FastAPI', 'Flask',
            'TensorFlow', 'PyTorch', 'Keras', 'Scikit-learn',
            'Machine Learning', 'Deep Learning', 'NLP', 'Computer Vision',
            'Docker', 'Kubernetes', 'AWS', 'GCP', 'Azure',
            'SQL', 'PostgreSQL', 'MongoDB', 'Redis',
            'Git', 'Linux', 'Bash', 'REST API', 'GraphQL',
            'ROS', 'Embedded', 'FPGA', 'Robotics', 'IoT',
            'MLOps', 'Data Science', 'AI', 'LLM', 'RAG',
        ]

        found_skills = []
        text_lower = text.lower()

        for skill in skill_patterns:
            if skill.lower() in text_lower:
                found_skills.append(skill)

        return found_skills
