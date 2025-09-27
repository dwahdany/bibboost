# BibBoost

A CLI tool to update BibTeX files with conference versions of papers using the Semantic Scholar API.

## Features

- **Interactive paper selection** - Choose from multiple versions with detailed information
- **Complete metadata replacement** - Uses Semantic Scholar's complete BibTeX entries
- **Smart preprint detection** - Only processes arXiv/preprint entries
- **Backup protection** - Creates backups before modifying files
- **Dry-run mode** - Preview changes without writing files

## Installation

```bash
uv add click bibtexparser requests python-dotenv questionary tenacity
```

## Usage

### Basic Usage

```bash
# Interactive update with complete metadata
uv run python main.py update-bib papers.bib

# Preview changes without modifying the file
uv run python main.py update-bib papers.bib --dry-run --verbose

# Save to a different output file
uv run python main.py update-bib papers.bib --output updated_papers.bib
```

### With API Key (Recommended)

Get a free API key from [Semantic Scholar](https://www.semanticscholar.org/product/api) for better rate limits:

1. Set environment variable:
```bash
export SEMANTIC_SCHOLAR_API_KEY="your-api-key"
uv run python main.py update-bib papers.bib
```

2. Or pass it directly:
```bash
uv run python main.py update-bib papers.bib --api-key "your-api-key"
```

### Options

- `--output/-o`: Specify output file (default: updates input file)
- `--api-key`: Semantic Scholar API key
- `--dry-run`: Preview changes without writing files
- `--verbose/-v`: Show detailed progress
- `--backup/--no-backup`: Create backup file (default: True)

## How It Works

1. **Parse BibTeX file** - Identifies preprint/arXiv entries (skips published papers)
2. **Search Semantic Scholar** - Finds all available versions of each paper
3. **Interactive selection** - Shows detailed paper information for user choice:
   - Original BibTeX entry details
   - All found versions with authors, venues, and years
   - Visual separators for easy scanning
4. **Complete replacement** - Uses Semantic Scholar's complete BibTeX citation
5. **Preserve citation keys** - Keeps your original IDs for existing citations

## Interactive Selection

When multiple versions are found, you'll see:

```
📄 Found multiple versions for: Attention Is All You Need

📚 Original BibTeX entry:
   ID: attention2017
   Title: Attention Is All You Need
   Authors: Ashish Vaswani and others
   Journal: arXiv preprint arXiv:1706.03762
   Year: 2017
   arXiv: 1706.03762

══════════════════════════════════════════════════════════════════════

? Choose the version to use:
 → Attention is All you Need
    Authors: Ashish Vaswani, Noam M. Shazeer, Niki Parmar, et al.
    Venue: Neural Information Processing Systems (2017) - Conference
    ────────────────────────────────────────────────────────────────

   Skip (keep original version)
```

## Complete Metadata Replacement

The tool uses Semantic Scholar's `citationStyles.bibtex` field to get complete, properly formatted entries:

**Before (arXiv preprint):**
```bibtex
@article{attention2017,
  title={Attention Is All You Need},
  author={Ashish Vaswani and others},
  journal={arXiv preprint arXiv:1706.03762},
  year={2017}
}
```

**After (complete conference version):**
```bibtex
@article{attention2017,
  author = {Ashish Vaswani and Noam M. Shazeer and Niki Parmar and Jakob Uszkoreit and Llion Jones and Aidan N. Gomez and Lukasz Kaiser and I. Polosukhin},
  booktitle = {Neural Information Processing Systems},
  pages = {5998-6008},
  title = {Attention is All you Need},
  year = {2017}
}
```

**Benefits:**
- ✅ Complete author lists (not truncated)
- ✅ Exact venue names and formatting
- ✅ Page numbers, volumes, and other metadata
- ✅ Proper BibTeX formatting from authoritative source
- ✅ No manual field mapping required