"""BibTeX file processor for updating entries with conference versions."""

import re
from typing import Dict, Any, List, Optional, Tuple
import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.bwriter import BibTexWriter
from bibtexparser.bibdatabase import BibDatabase
import questionary
from questionary import Style

from dblp_client import DBLPClient


class BibUpdater:
    """Updates BibTeX entries with conference versions of papers."""

    def __init__(self, dblp_client: DBLPClient):
        """Initialize with a DBLP client."""
        self.client = dblp_client

    def load_bib_file(self, file_path: str) -> BibDatabase:
        """Load and parse a BibTeX file."""
        with open(file_path, 'r', encoding='utf-8') as bib_file:
            parser = BibTexParser(common_strings=True)
            parser.ignore_nonstandard_types = False
            return bibtexparser.load(bib_file, parser=parser)

    def save_bib_file(self, bib_database: BibDatabase, file_path: str) -> None:
        """Save a BibTeX database to file."""
        writer = BibTexWriter()
        writer.indent = '  '
        writer.align_values = True

        with open(file_path, 'w', encoding='utf-8') as bib_file:
            bibtexparser.dump(bib_database, bib_file, writer=writer)

    def extract_title_and_arxiv(self, entry: Dict[str, str]) -> Tuple[Optional[str], Optional[str]]:
        """Extract title and arXiv ID from a BibTeX entry."""
        title = entry.get('title', '').strip()

        # Clean up title (remove braces, extra whitespace)
        title = re.sub(r'[{}]', '', title)
        title = re.sub(r'\s+', ' ', title).strip()

        # Extract arXiv ID from various fields
        arxiv_id = None

        # Check eprint field
        if 'eprint' in entry and 'archiveprefix' in entry:
            if entry['archiveprefix'].lower() == 'arxiv':
                arxiv_id = entry['eprint']

        # Check URL field for arXiv links
        url = entry.get('url', '')
        arxiv_match = re.search(r'arxiv\.org/(?:abs/|pdf/)(\d+\.\d+)', url)
        if arxiv_match:
            arxiv_id = arxiv_match.group(1)

        # Check journal field for arXiv
        journal = entry.get('journal', '').lower()
        if 'arxiv' in journal:
            # Extract arXiv ID from journal field
            arxiv_match = re.search(r'(\d+\.\d+)', entry.get('journal', ''))
            if arxiv_match:
                arxiv_id = arxiv_match.group(1)

        return title if title else None, arxiv_id

    def is_preprint_entry(self, entry: Dict[str, str]) -> bool:
        """Check if a BibTeX entry represents a preprint/arXiv paper."""
        # If it already has a conference venue (booktitle), it's published
        if 'booktitle' in entry and entry['booktitle'].strip():
            return False

        # If it has a journal that's not arXiv, it's published
        journal = entry.get('journal', '').lower()
        if journal and 'arxiv' not in journal and 'preprint' not in journal:
            return False

        # Check for arXiv indicators
        arxiv_indicators = [
            entry.get('eprint', ''),
            entry.get('journal', '').lower(),
            entry.get('url', '').lower(),
            entry.get('note', '').lower()
        ]

        return any('arxiv' in indicator for indicator in arxiv_indicators)

    def parse_bibtex_entry(self, bibtex_string: str) -> Dict[str, str]:
        """Parse a BibTeX string and return the entry fields."""
        try:
            parser = BibTexParser(common_strings=True)
            parser.ignore_nonstandard_types = False
            bib_database = bibtexparser.loads(bibtex_string, parser=parser)

            if bib_database.entries:
                return bib_database.entries[0]
            return {}
        except Exception as e:
            print(f"Error parsing BibTeX: {e}")
            return {}

    def update_entry_with_conference_version(self, entry: Dict[str, str], paper_data: Dict[str, Any]) -> Dict[str, str]:
        """Update a BibTeX entry with DBLP data."""
        # Get the clean BibTeX from DBLP
        bibtex_citation = paper_data.get('bibtex', '')

        if bibtex_citation:
            # Parse the BibTeX from DBLP
            dblp_entry = self.parse_bibtex_entry(bibtex_citation)

            if dblp_entry:
                # Keep the original ID but use everything else from DBLP
                updated_entry = dblp_entry.copy()
                updated_entry['ID'] = entry.get('ID', dblp_entry.get('ID', ''))
                return updated_entry

        # Fallback: if no BibTeX available, return original entry unchanged
        return entry

    def format_paper_option(self, paper: Dict[str, Any]) -> str:
        """Format a paper for display in the interactive selection."""
        # Basic paper info
        title = paper.get("title", "Unknown title")
        year = paper.get("year", "Unknown year")

        # Venue information from DBLP
        venue_name = paper.get("venue", "Unknown venue")
        paper_type = paper.get("type", "")

        # Authors from DBLP (limit to first 3 for readability)
        authors = paper.get("authors", [])
        if authors:
            # Authors are already strings from DBLP
            author_names = [author for author in authors[:3] if author.strip()]
            if len(authors) > 3:
                author_str = ", ".join(author_names) + ", et al."
            else:
                author_str = ", ".join(author_names)
        else:
            author_str = "Unknown authors"

        # Create venue info with type
        venue_info = f"{venue_name} ({year})"
        if paper_type:
            venue_info += f" - {paper_type}"

        # Truncate title if too long
        if len(title) > 60:
            title = title[:57] + "..."

        # Add visual separator
        separator = "─" * 60
        return f"{title}\n    Authors: {author_str}\n    Venue: {venue_info}\n    {separator}"

    def select_paper_version(self, title: str, papers: List[Dict[str, Any]], original_entry: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """
        Select the best paper version interactively.

        Args:
            title: The paper title for display
            papers: List of paper versions
            original_entry: The original BibTeX entry being updated

        Returns:
            Selected paper or None if user chooses to skip
        """
        if not papers:
            return None

        # If only one option, still show it for confirmation
        if len(papers) == 1:
            papers = papers  # Show the single option for user confirmation

        # Prepare choices for interactive selection
        choices = []

        # Add paper options
        for paper in papers:
            option_text = self.format_paper_option(paper)
            choices.append({
                "name": option_text,
                "value": paper
            })

        # Add skip option with separator
        choices.append({
            "name": f"    {'═' * 60}\n    Skip (keep original version)",
            "value": None
        })

        # Define custom style for better visibility
        custom_style = Style([
            ('qmark', 'fg:#ff9d00 bold'),           # Question mark
            ('question', 'bold'),                    # Question text
            ('answer', 'fg:#ff9d00 bold'),          # Selected answer
            ('pointer', 'fg:#ff9d00 bold'),         # Selection pointer
            ('highlighted', 'fg:#ff9d00 bold'),     # Highlighted option
            ('selected', 'fg:#cc5454'),             # Selected option
            ('separator', 'fg:#6C6C6C'),            # Separator lines
        ])

        # Show interactive selection
        try:
            print(f"\n📄 Found multiple versions for: {title}")
            print(f"\n📚 Original BibTeX entry:")
            print(f"   ID: {original_entry.get('ID', 'Unknown')}")
            print(f"   Title: {original_entry.get('title', 'Unknown')}")
            print(f"   Authors: {original_entry.get('author', 'Unknown')}")

            # Show original venue info
            if 'journal' in original_entry:
                print(f"   Journal: {original_entry['journal']}")
            if 'booktitle' in original_entry:
                print(f"   Booktitle: {original_entry['booktitle']}")
            if 'year' in original_entry:
                print(f"   Year: {original_entry['year']}")
            if 'eprint' in original_entry:
                print(f"   arXiv: {original_entry['eprint']}")

            print(f"\n{'═' * 70}")  # Major separator
            print()  # Empty line for spacing

            selected = questionary.select(
                "Choose the version to use:",
                choices=choices,
                pointer="→",
                style=custom_style,
                use_shortcuts=True
            ).ask()

            return selected

        except (KeyboardInterrupt, EOFError):
            # User cancelled, skip this paper
            return None

    def process_bib_file(self, input_path: str, output_path: str, dry_run: bool = False, verbose: bool = False, interactive: bool = True) -> Tuple[int, int]:
        """
        Process a BibTeX file to update preprint entries with conference versions.

        Returns:
            Tuple of (total_processed, total_updated)
        """
        # Load the BibTeX file
        bib_database = self.load_bib_file(input_path)

        total_processed = 0
        total_updated = 0

        for entry in bib_database.entries:
            total_processed += 1

            if verbose:
                print(f"Processing entry: {entry.get('ID', 'Unknown')}")

            # Check if this is a preprint entry
            is_preprint = self.is_preprint_entry(entry)
            if verbose:
                print(f"  Is preprint check: {is_preprint}")
                if 'booktitle' in entry:
                    print(f"  Has booktitle: '{entry['booktitle']}'")
                if 'journal' in entry:
                    print(f"  Has journal: '{entry['journal']}'")

            if not is_preprint:
                if verbose:
                    print(f"  Skipping non-preprint entry")
                continue

            # Extract title and arXiv ID
            title, arxiv_id = self.extract_title_and_arxiv(entry)

            if not title:
                if verbose:
                    print(f"  Could not extract title, skipping")
                continue

            if verbose:
                print(f"  Searching DBLP for: {title}")
                if arxiv_id:
                    print(f"  arXiv ID: {arxiv_id}")

            # Search DBLP for published versions
            all_versions = self.client.search_and_get_bibtex(title)

            if verbose:
                print(f"  Found {len(all_versions)} total results from DBLP")
                for i, paper in enumerate(all_versions):
                    venue = paper.get('venue', 'Unknown')
                    year = paper.get('year', 'Unknown')
                    is_published = self.client.is_published_venue(paper)
                    print(f"    {i+1}. {venue} ({year}) - Published: {is_published}")

            # Filter to only published versions (not preprints)
            published_versions = [
                paper for paper in all_versions
                if self.client.is_published_venue(paper)
            ]

            if verbose:
                print(f"  After filtering: {len(published_versions)} published versions")

            if published_versions:
                # Select the version to use
                selected_paper = self.select_paper_version(title, published_versions, entry)

                if selected_paper:
                    # Debug: check if selected_paper is actually a dict
                    if not isinstance(selected_paper, dict):
                        if verbose:
                            print(f"  Error: Selected paper is not a dict: {type(selected_paper)} = {selected_paper}")
                        continue

                    if verbose:
                        venue_name = selected_paper.get('venue', 'Unknown venue')
                        year = selected_paper.get('year', 'Unknown year')
                        print(f"  Selected: {venue_name} ({year})")

                    if not dry_run:
                        # Update the entry
                        updated_entry = self.update_entry_with_conference_version(entry, selected_paper)

                        # Replace the entry in the database
                        for i, existing_entry in enumerate(bib_database.entries):
                            if existing_entry['ID'] == entry['ID']:
                                bib_database.entries[i] = updated_entry
                                break

                    total_updated += 1
                else:
                    if verbose:
                        print(f"  Skipped (user choice)")
            else:
                if verbose:
                    print(f"  No published versions found")

        # Save the updated file (unless dry run)
        if not dry_run and total_updated > 0:
            self.save_bib_file(bib_database, output_path)

        return total_processed, total_updated