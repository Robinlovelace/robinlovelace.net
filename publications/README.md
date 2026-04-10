# Publications Import Workflow

This directory contains generated Quarto publication pages plus a machine-readable
listing file derived from a BibTeX source.

## Overview

The goal of this directory is to provide a searchable, modern interface for all
publications while maintaining URL compatibility with the previous `blogdown` website
wherever possible.

## What This Produces

Running the importer creates:

- `publications/<slug>/index.qmd`
  A generated Quarto page for one publication.
- `publications/<slug>/entry.bib`
  The original BibTeX entry for that publication.
- `publications/<slug>/_notes.qmd`
  A manual notes file that is **not** overwritten on re-import. Use this for 
  adding extra links, PDFs, or commentary.
- `publications/publications.yml`
  A structured data file for the Quarto listing in `publications.qmd`.
- `files/bibliography/my-citations-for-web.bib`
  A repo-local copy of the imported source BibTeX file.

## URL Compatibility

The previous site served publications at `/publication/<slug>/`.
This site serves them at `/publications/<slug>/`.

> **Note:** We added an 's' to the directory name to follow the plural convention 
> used for `/posts/`. Redirects should be handled in the web server configuration 
> (e.g., `_redirects` for Netlify or `.htaccess` for Apache).

### Slug Mapping

Slugs are derived from BibTeX keys. 
- `key_name_2024` -> `key-name-2024`
- `key_name_2024a` -> `key-name-2024a`

*Comparison with old site:* Some old slugs had extra hyphens (e.g., `2022-b` instead 
of `2022b`). If strict URL parity is required for a specific paper, you can 
manually set a redirect or adjust the BibTeX key.

## How It Works

The importer lives at [`scripts/import_publications.py`](../scripts/import_publications.py).

It uses:

1. `pandoc -f bibtex -t csljson` to parse the BibTeX safely.
2. A Python script to normalize metadata and generate the file structure.
3. `_notes.qmd` inclusion to allow persistent manual edits.

The script intentionally avoids external Python package dependencies (like `bibtexparser`)
to ensure it runs anywhere Quarto is installed.

## Importing New Entries

1. Update your BibTeX file (e.g., from Zotero).
2. Run the importer:

```bash
python3 scripts/import_publications.py path/to/your/export.bib
```

3. Render the site:

```bash
quarto render
```

## What Gets Overwritten

| File | Overwritten? |
|------|--------------|
| `publications/<slug>/index.qmd` | Yes |
| `publications/<slug>/entry.bib` | Yes |
| `publications/publications.yml` | Yes |
| `publications/<slug>/_notes.qmd` | **No** |

## Future Plans

- **Automated PDFs:** Link to local PDF files if they exist in `files/publications/`.
- **Enhanced Metadata:** Support for "Featured" publications and "Projects" association.
- **DataTables:** If the publication list grows very large, we may switch from 
  Quarto listings to a full DataTables implementation for even faster filtering.
