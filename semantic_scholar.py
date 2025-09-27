"""Semantic Scholar API client for finding conference versions of papers."""

import time
import requests
from typing import Optional, Dict, Any, List
from urllib.parse import quote

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log
)
import logging


class SemanticScholarClient:
    """Client for interacting with the Semantic Scholar Academic Graph API."""

    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    def __init__(self, api_key: Optional[str] = None, verbose: bool = False):
        """Initialize the client with optional API key."""
        self.api_key = api_key
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({"x-api-key": api_key})

        # Set up logging for retry attempts
        self.logger = logging.getLogger(__name__)
        if verbose:
            logging.basicConfig(level=logging.INFO)

        # Rate limiting: be conservative with requests
        self.last_request_time = 0
        # More conservative rate limiting without API key
        self.min_request_interval = 2.0 if not api_key else 0.1

    def _should_retry(self, exception):
        """Determine if an exception should trigger a retry."""
        if isinstance(exception, requests.exceptions.HTTPError):
            # Only retry on rate limits (429) and server errors (5xx)
            status_code = exception.response.status_code if exception.response else 0
            return status_code == 429 or status_code >= 500
        # Retry on network/connection errors
        return isinstance(exception, (requests.exceptions.ConnectionError, requests.exceptions.Timeout))

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=60),
        retry=retry_if_exception_type((requests.exceptions.RequestException,)),
        before_sleep=before_sleep_log(logging.getLogger(__name__), logging.INFO),
        after=after_log(logging.getLogger(__name__), logging.INFO)
    )
    def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make a rate-limited request to the API with exponential backoff retry."""
        # Simple rate limiting
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)

        url = f"{self.BASE_URL}/{endpoint}"
        response = self.session.get(url, params=params)
        self.last_request_time = time.time()

        # Handle rate limiting specifically
        if response.status_code == 429:
            retry_after = response.headers.get('Retry-After')
            if retry_after:
                self.logger.info(f"Rate limited. Waiting {retry_after} seconds before retry.")
                time.sleep(int(retry_after))
            raise requests.exceptions.HTTPError(f"Rate limited: {response.status_code}", response=response)

        response.raise_for_status()
        return response.json()

    def search_paper_by_title(self, title: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for papers by title using relevance search."""
        params = {
            "query": title,
            "limit": limit,
            "fields": "paperId,title,authors,venue,publicationVenue,year,publicationTypes,citationStyles"
        }

        try:
            result = self._make_request("paper/search", params)
            if not result:
                self.logger.warning(f"No result returned for query: {title}")
                return []
            data = result.get("data", [])
            if not data:
                self.logger.info(f"No papers found for query: {title}")
                return []
            return data
        except Exception as e:
            self.logger.error(f"Error searching for paper '{title}': {e}")
            return []

    def get_paper_details(self, paper_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific paper."""
        params = {
            "fields": "paperId,title,authors,venue,publicationVenue,year,publicationTypes,abstract,citationStyles"
        }

        try:
            return self._make_request(f"paper/{paper_id}", params)
        except Exception as e:
            self.logger.error(f"Error getting paper details for ID '{paper_id}': {e}")
            return None

    def find_all_versions(self, title: str, arxiv_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Find all published versions of a paper, given its title and optional arXiv ID.

        Returns a list of papers with quality ranking metadata.
        """
        papers = self.search_paper_by_title(title)

        if not papers:
            return []

        # Rank papers by venue type and prestige
        ranked_papers = []

        for paper in papers:
            if not paper:  # Skip None papers
                continue

            venue = paper.get("publicationVenue") or {}
            pub_types = paper.get("publicationTypes") or []

            # Get venue name from publicationVenue or fallback to venue field
            venue_name = venue.get("name", "") if venue else ""
            if not venue_name:
                venue_name = paper.get("venue", "")
            venue_name_lower = venue_name.lower() if venue_name else ""

            # Skip if this is the arXiv version we're trying to replace
            # Note: API doesn't return arxivId field, so we'll rely on other filtering

            # Determine venue type for display only
            if venue.get("type") == "conference":
                quality_label = "Conference"
            elif "Conference" in pub_types:
                quality_label = "Conference"
            elif "JournalArticle" in pub_types:
                quality_label = "Journal"
            else:
                quality_label = "Other"

            # Add venue type metadata for display
            paper_with_meta = paper.copy()
            paper_with_meta["_quality_label"] = quality_label
            paper_with_meta["_venue_type"] = venue.get("type", "unknown")

            ranked_papers.append(paper_with_meta)

        # Return papers in API order (no automatic ranking)
        return ranked_papers

    def find_conference_version(self, title: str, arxiv_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Find the best conference version of a paper (for automatic mode).

        This is kept for backward compatibility with automatic selection.
        """
        versions = self.find_all_versions(title, arxiv_id)
        return versions[0] if versions else None

    def is_conference_venue(self, paper: Dict[str, Any]) -> bool:
        """Check if a paper is published in a conference venue."""
        if not paper:
            return False

        venue = paper.get("publicationVenue", {}) or {}
        pub_types = paper.get("publicationTypes", []) or []

        return (
            (venue and venue.get("type") == "conference") or
            "Conference" in pub_types or
            "JournalArticle" in pub_types
        )