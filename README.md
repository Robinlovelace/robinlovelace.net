

# robinlovelace.net

This is the repository for the personal, academic, and professional
website of **Robin Lovelace** (Associate Professor of Transport Data
Science at the Leeds Institute for Transport Studies), hosted at
[robinlovelace.net](https://www.robinlovelace.net).

The website is built using [Quarto](https://quarto.org) and is
configured to deploy automatically via GitHub Pages.

------------------------------------------------------------------------

## 🚀 Key Features & Customizations

This site is based on a Quarto academic template but has been heavily
customized with several advanced features and automation scripts:

1.  **Automated Publications Manager**:
    - **Canonical Source**: Publications are managed inside the BibTeX
      file `references.bib`.
    - **Automation Script**:
      [`scripts/generate_publications_yml.py`](file:///home/robin/github/robinlovelace/robinlovelace.net/scripts/generate_publications_yml.py)
      parses the `.bib` file (using a custom stdlib-only parser with
      nested brace support) and auto-generates the `publications.yml`
      database during the build pipeline.
    - **Interactive Page**: The publications page is render-optimized
      and supports sorting, filtering, and dynamic Academicons link
      integration.
2.  **Legacy Redirects for GitHub Pages**:
    - **Problem**: GitHub Pages does not support Netlify’s `_redirects`
      file natively.
    - **Solution**:
      [`scripts/generate_html_redirects.py`](file:///home/robin/github/robinlovelace/robinlovelace.net/scripts/generate_html_redirects.py)
      parses the Netlify-style redirects and compiles them into static
      HTML stubs containing `<meta http-equiv="refresh" ...>` tags
      inside the built site directory.
3.  **Pre-commit File Size Guard**:
    - A custom pre-commit hook in
      [`.githooks/pre-commit`](file:///home/robin/github/robinlovelace/robinlovelace.net/.githooks/pre-commit)
      automatically prevents files larger than **1 MB** from being
      committed, keeping the repository history clean and lightweight.
4.  **Giscus Comments**:
    - Blog posts in `/posts/` feature interactive comments powered by
      [Giscus](https://giscus.app) with automatic theme matching.
5.  **Integrated Development Container**:
    - The repository features a pre-configured
      [`.devcontainer/`](file:///home/robin/github/robinlovelace/robinlovelace.net/.devcontainer)
      utilizing the `ghcr.io/geocompx/pythonr` image, providing a
      unified, ready-to-use R and Python environment for local rendering
      and development.

------------------------------------------------------------------------

## 🛠 Local Development

### Option A: Using VS Code Dev Containers (Recommended)

1.  Open this workspace in VS Code.

2.  Click **Reopen in Container** when prompted (or open the Command
    Palette and select `Dev Containers: Reopen in Container`).

3.  Render and preview the site using the integrated terminal:

    ``` bash
    quarto preview
    ```

### Option B: Local Installation

Ensure you have [Quarto installed](https://quarto.org/docs/get-started/)
on your local machine, then run:

- **Preview the website locally**:

  ``` bash
  quarto preview
  ```

- **Build/Render the static site**:

  ``` bash
  quarto render
  ```

------------------------------------------------------------------------

## 📝 Creating a New Post

To create a new post with today’s date, load the helper function and use
it:

``` r
devtools::load_all()
create_post("Your Post Title", slug = "your-post-slug")
```

Or with tags and categories:

``` r
devtools::load_all()
create_post(
  title = "Advanced Quarto Tips",
  slug = "quarto-tips",
  tags = c("quarto", "tips"),
  categories = c("tutorial")
)
```

The post folder and `index.qmd` are created automatically with today’s
date and YAML frontmatter. Run `quarto preview` to see it live.

------------------------------------------------------------------------

## 🔒 Activating the File Size Hook

To enforce the 1 MB file size limit on your local commits:

``` bash
git config core.hooksPath .githooks
chmod +x .githooks/pre-commit
```

If you ever need to bypass this hook to commit a large file, commit with
the `--no-verify` flag:

``` bash
git commit -m "Commit message" --no-verify
```
