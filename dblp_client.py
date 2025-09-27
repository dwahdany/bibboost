"""DBLP API client for finding published versions of papers."""

import requests
from typing import Optional, Dict, Any, List
from urllib.parse import quote


class DBLPClient:
    """Client for interacting with the DBLP Computer Science Bibliography API."""

    BASE_URL = "https://dblp.org"

    def __init__(self):
        """Initialize the DBLP client."""
        self.session = requests.Session()

    def search_papers_by_title(self, title: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for papers by title using DBLP publication search."""
        url = f"{self.BASE_URL}/search/publ/api"
        params = {
            "q": title,  # Let requests handle the encoding
            "format": "json",
            "h": limit
        }

        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            result = data.get("result", {})

            # Debug: print the search URL and basic response info
            print(f"DEBUG: Searching DBLP: {response.url}")
            print(f"DEBUG: Response status: {response.status_code}")
            print(f"DEBUG: Result status: {result.get('status', 'No status')}")

            hits = result.get("hits", {})
            hit_list = hits.get("hit", [])

            print(f"DEBUG: Raw hit_list type: {type(hit_list)}, length: {len(hit_list) if isinstance(hit_list, list) else 'not list'}")

            # Normalize to always be a list
            if isinstance(hit_list, dict):
                hit_list = [hit_list]

            papers = []
            for hit in hit_list:
                info = hit.get("info", {})

                # Extract authors
                authors_data = info.get("authors", {})
                if isinstance(authors_data, dict):
                    author_list = authors_data.get("author", [])
                    if isinstance(author_list, dict):
                        author_list = [author_list]
                    authors = [author.get("text", "") for author in author_list]
                else:
                    authors = []

                paper = {
                    "key": info.get("key", ""),
                    "title": info.get("title", ""),
                    "venue": info.get("venue", ""),
                    "year": info.get("year", ""),
                    "authors": authors,
                    "doi": info.get("doi", ""),
                    "url": info.get("url", ""),
                    "type": info.get("type", ""),
                    "_dblp_key": info.get("key", "")  # Store for BibTeX fetching
                }
                papers.append(paper)

            return papers

        except requests.RequestException as e:
            print(f"Error searching DBLP for '{title}': {e}")
            return []

    def get_bibtex(self, dblp_key: str) -> Optional[str]:
        """Fetch the BibTeX entry for a paper using its DBLP key."""
        if not dblp_key:
            return None

        bibtex_url = f"{self.BASE_URL}/rec/{dblp_key}.bib"

        try:
            response = self.session.get(bibtex_url)
            response.raise_for_status()
            return response.text.strip()

        except requests.RequestException as e:
            print(f"Error fetching BibTeX for key '{dblp_key}': {e}")
            return None

    def search_and_get_bibtex(self, title: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for papers and include BibTeX data for each result."""
        papers = self.search_papers_by_title(title, limit)

        for paper in papers:
            dblp_key = paper.get("_dblp_key")
            if dblp_key:
                bibtex = self.get_bibtex(dblp_key)
                paper["bibtex"] = bibtex

        return papers

    def is_published_venue(self, paper: Dict[str, Any]) -> bool:
        """Check if a paper is published in a proper venue (not arXiv/preprint)."""
        venue = paper.get("venue", "").lower()
        paper_type = paper.get("type", "").lower()

        # Skip obvious preprint venues
        preprint_indicators = ["arxiv", "corr", "preprint"]
        return not any(indicator in venue for indicator in preprint_indicators)