# Publications Import Workflow

This directory contains generated Quarto publication pages plus a machine-readable
listing file derived from a BibTeX source.

## What This Produces

Running the importer creates:

- `publications/<slug>/index.qmd`
  A generated Quarto page for one publication.
- `publications/<slug>/entry.bib`
  The original BibTeX entry for that publication.
- `publications/<slug>/_notes.qmd`
  A manual notes file that is **not** overwritten on re-import.
- `publications/publications.yml`
  A structured data file for future Quarto listings, DataTables, or other JS-powered tables.
- `files/bibliography/my-citations-for-web.bib`
  A repo-local copy of the imported source BibTeX file.

## How It Works

The importer lives at [`scripts/import_publications.py`](../scripts/import_publications.py).

It uses:

1. `pandoc -f bibtex -t csljson` to parse the BibTeX safely.
2. A small Python generator to normalize metadata and create Quarto pages.
3. A stable output layout so the generated pages can later feed:
   - Quarto native listings
   - DataTables or other JS table UIs
   - custom per-publication landing pages

The script intentionally avoids external Python package dependencies. That keeps
the workflow easy to rerun on any machine with Quarto/Pandoc installed.

## Importing New Entries

If you have a refreshed BibTeX export, replace or update the source file and rerun
the importer.

### Option 1: Re-import from the old source file

```bash
python3 scripts/import_publications.py /tmp/old-robinlovelace/static/bibs/my-citations-for-web.bib
```

### Option 2: Re-import from the repo-local copy

```bash
python3 scripts/import_publications.py files/bibliography/my-citations-for-web.bib
```

### Typical workflow

1. Export fresh BibTeX from Zotero or another reference manager.
2. Replace `files/bibliography/my-citations-for-web.bib` with the new export.
3. Run:

```bash
python3 scripts/import_publications.py files/bibliography/my-citations-for-web.bib
```

4. Review the changes with `git diff`.
5. Render the site with `quarto render`.

## What Gets Overwritten

Each import overwrites:

- `publications/<slug>/index.qmd`
- `publications/<slug>/entry.bib`
- `publications/publications.yml`
- `files/bibliography/my-citations-for-web.bib` if the import source is different

Each import does **not** overwrite:

- `publications/<slug>/_notes.qmd`

That means any manual additions for a paper should go into `_notes.qmd`, not directly
into `index.qmd`.

## Current Design Choice

The importer is kept inside this repo for now because:

- the metadata schema is still evolving
- Quarto publication conventions here are site-specific
- keeping it local makes iteration faster than managing a separate package/submodule

## Options For Splitting Out The Logic Later

### Option 1: Keep it repo-local

Best if:

- this workflow is mainly for this site
- the metadata schema is still changing
- you want the lowest maintenance overhead

### Option 2: Extract to a standalone Python package

Best if:

- you want a reusable CLI such as `quarto-publications import input.bib output/`
- other sites may use the same workflow
- you want tests, versioning, and pinned releases

Suggested shape:

- repo with `src/` package layout
- CLI entry point
- templates for Quarto page generation
- optional outputs for `.qmd`, YAML, JSON

This is the most practical extraction path because the current implementation is
already Python and already uses Pandoc as the parser.

### Option 3: Extract to a thin standalone repo and vendor it back in

Best if:

- you want independent version control
- you are not ready to publish a package yet

In that case, prefer:

- standalone repo
- install or invoke via `uv run` or `python -m`

Avoid a git submodule until the API and output schema stabilize. A submodule is
extra coordination cost with little benefit at this stage.

### Option 4: Rebuild as an R package

Best if:

- you want the workflow to live in an R/Zotero/bookdown/blogdown ecosystem
- you prefer maintaining tooling in R

This is viable, but less direct than the current approach because Pandoc + Python
already solves the parsing and file generation cleanly.

### Option 5: Rebuild in Rust or another compiled language

Best if:

- performance, binary distribution, or very robust parsing becomes important
- the tool grows into something broader than this site

This is not justified yet. The current bottleneck is schema design, not runtime speed.

## Recommended Next Step

If this workflow continues to be useful after the publication index and per-paper
pages settle down, extract the script into a small standalone Python repo and keep
this site consuming released versions of it.
