"""CLI application to update BibTeX files with conference versions of papers."""

import os
import sys
import shutil
import glob
from pathlib import Path
from typing import Optional

import click
from dotenv import load_dotenv

from dblp_client import DBLPClient
from bib_updater import BibUpdater


load_dotenv()


@click.command()
@click.argument('input_file', type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option('--output', '-o', type=click.Path(dir_okay=False, path_type=Path),
              help='Output file path. If not specified, updates the input file.')
@click.option('--dry-run', is_flag=True,
              help='Preview changes without modifying files.')
@click.option('--verbose', '-v', is_flag=True,
              help='Show detailed progress information.')
@click.option('--backup/--no-backup', default=True,
              help='Create backup file before updating (default: True).')
def update_bib(input_file: Path, output: Optional[Path],
               dry_run: bool, verbose: bool, backup: bool) -> None:
    """Update BibTeX file with conference versions of papers.

    This tool searches for conference versions of preprint/arXiv papers in your
    BibTeX file and updates the entries with proper venue information.

    INPUT_FILE: Path to the BibTeX file to process.
    """
    # Note: DBLP doesn't require API keys

    # Determine output file
    output_file = output or input_file

    # Create backup if requested and not doing dry run
    backup_file = None
    if backup and not dry_run and output_file == input_file:
        # Find next available backup number using glob and sorting
        pattern = f"{input_file.stem}{input_file.suffix}.backup.*"
        existing_backups = glob.glob(str(input_file.parent / pattern))

        # Extract numbers from existing backups and find the next one
        def extract_backup_number(backup_path):
            try:
                return int(Path(backup_path).suffix[1:])  # Remove the dot and convert
            except ValueError:
                return None

        backup_numbers = list(filter(None, map(extract_backup_number, existing_backups)))
        next_number = max(backup_numbers, default=0) + 1
        backup_file = input_file.with_suffix(f'{input_file.suffix}.backup.{next_number:03d}')

        if verbose:
            click.echo(f"Creating backup: {backup_file}")
        shutil.copy2(input_file, backup_file)

    # Initialize clients
    if verbose:
        click.echo("Initializing DBLP client...")

    dblp_client = DBLPClient()
    updater = BibUpdater(dblp_client)

    try:
        if verbose:
            click.echo(f"Processing file: {input_file}")
            if dry_run:
                click.echo("Running in dry-run mode - no files will be modified")

        # Process the file
        total_processed, total_updated = updater.process_bib_file(
            str(input_file),
            str(output_file),
            dry_run=dry_run,
            verbose=verbose,
            interactive=True
        )

        # Report results
        click.echo(f"\nResults:")
        click.echo(f"  Total entries processed: {total_processed}")
        click.echo(f"  Entries updated: {total_updated}")

        if total_updated > 0:
            if dry_run:
                click.echo(f"  Run without --dry-run to apply changes")
            else:
                click.echo(f"  Updated file saved to: {output_file}")
                if backup and backup_file and output_file == input_file:
                    click.echo(f"  Backup saved to: {backup_file}")
        else:
            click.echo("  No updates needed")

    except Exception as e:
        click.echo(f"Error processing file: {e}", err=True)
        sys.exit(1)


@click.group()
def cli():
    """Scholarly: Tools for managing academic bibliographies."""
    pass


cli.add_command(update_bib)


if __name__ == "__main__":
    cli()
