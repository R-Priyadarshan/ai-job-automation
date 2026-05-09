"""
============================================================
src/scrapers/base_scraper.py
------------------------------------------------------------
PURPOSE:
    Defines the BaseScraper class that ALL scrapers inherit from.
    This ensures every scraper has the same interface and shared
    helper methods (request handling, politeness delays, etc.)

CONCEPT: Abstract Base Class (ABC)
    Think of this as a template or contract:
    - Every child scraper MUST implement `scrape()` method
    - All scrapers get shared helpers for free

ARCHITECTURE:
    BaseScraper
    ├── RemoteOKScraper
    ├── WeWorkRemotelyScraper
    ├── IntershalaScraper
    └── LinkedInScraper
============================================================
"""

import time                          # For polite delays between requests
import random                        # Random delay variation
import requests                      # HTTP requests library
from abc import ABC, abstractmethod  # Abstract base class tools
from typing import Optional          # Type hints
from loguru import logger            # Logging
from fake_useragent import UserAgent # Rotate browser user-agents


class BaseScraper(ABC):
    """
    Abstract base class for all job scrapers.

    Every child scraper must implement the `scrape()` method.
    This class provides shared request handling and utilities.
    """

    def __init__(self, config: dict):
        """
        Initialize the scraper with configuration.

        Args:
            config: The full config dict from config.yaml
        """
        self.config = config
        self.scrape_config = config.get('scraping', {})

        # Maximum jobs to fetch from this source
        self.max_jobs = self.scrape_config.get('max_jobs_per_site', 50)

        # Seconds to wait between requests (be polite to websites!)
        self.delay = self.scrape_config.get('delay_between_requests', 2)

        # Keywords to search for
        self.keywords = self.scrape_config.get('keywords', ['software engineer'])

        # Initialize fake user agent rotator
        # This makes our requests look like they come from different browsers
        try:
            self.ua = UserAgent()
        except Exception:
            # Fallback if fake-useragent fails to download database
            self.ua = None

        # Create a requests Session for connection reuse (faster)
        self.session = requests.Session()

        logger.debug(f"{self.__class__.__name__} initialized.")

    def _get_headers(self) -> dict:
        """
        Returns HTTP headers that mimic a real browser.
        Rotating user agents helps avoid getting blocked.

        Returns:
            dict: Headers to include with every request.
        """
        if self.ua:
            try:
                user_agent = self.ua.random  # Random browser user agent
            except Exception:
                user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        else:
            user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"

        return {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    def _polite_delay(self):
        """
        Waits a random amount of time between requests.
        This prevents overwhelming servers and avoids rate limiting.
        Formula: delay ± 50% random variation
        """
        # Add randomness: e.g., if delay=2, actual delay is 1.0 to 3.0 seconds
        actual_delay = self.delay * (0.5 + random.random())
        logger.debug(f"Waiting {actual_delay:.1f} seconds (polite delay)...")
        time.sleep(actual_delay)

    def _safe_get(self, url: str, timeout: int = 15) -> Optional[requests.Response]:
        """
        Makes a safe HTTP GET request with error handling.

        Args:
            url: URL to fetch.
            timeout: Max seconds to wait for response.

        Returns:
            Response object, or None if request failed.
        """
        try:
            response = self.session.get(
                url,
                headers=self._get_headers(),
                timeout=timeout
            )

            # Raise exception for HTTP error codes (404, 500, etc.)
            response.raise_for_status()

            return response

        except requests.exceptions.ConnectionError:
            logger.warning(f"Connection failed: {url}")
            return None
        except requests.exceptions.Timeout:
            logger.warning(f"Request timed out: {url}")
            return None
        except requests.exceptions.HTTPError as e:
            logger.warning(f"HTTP error {e.response.status_code}: {url}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching {url}: {e}")
            return None

    @abstractmethod
    def scrape(self) -> list[dict]:
        """
        ABSTRACT METHOD — Must be implemented by each child class.

        Returns:
            List of job dictionaries, each with keys:
            {
                'title': str,
                'company': str,
                'location': str,
                'url': str,
                'source': str,
                'description': str,
                'skills': str,       # comma-separated
                'salary': str,
                'job_type': str,
                'posted_date': str,
            }
        """
        pass

    def _normalize_job(self, raw: dict) -> dict:
        """
        Normalizes a raw job dict to ensure all required keys exist.
        Fills in defaults for any missing fields.

        Args:
            raw: Raw job dictionary from scraping.

        Returns:
            Normalized job dictionary with all required fields.
        """
        return {
            'title':        raw.get('title', 'Unknown Title').strip(),
            'company':      raw.get('company', 'Unknown Company').strip(),
            'location':     raw.get('location', 'Remote'),
            'url':          raw.get('url', '').strip(),
            'source':       raw.get('source', 'unknown'),
            'description':  raw.get('description', ''),
            'skills':       raw.get('skills', ''),
            'salary':       raw.get('salary', 'Not specified'),
            'job_type':     raw.get('job_type', 'Full-time'),
            'posted_date':  raw.get('posted_date', ''),
        }
