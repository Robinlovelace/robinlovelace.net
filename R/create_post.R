#' Create a New Blog Post
#'
#' Creates a new blog post with today's date and a template index.qmd file.
#'
#' @param title Character string. The title of the post.
#' @param slug Character string. URL-friendly slug for the post folder
#'   (e.g., "quarto-migration-tips"). Hyphens are recommended.
#' @param date Character string or Date object. Defaults to today's date
#'   in "YYYY-MM-DD" format.
#' @param tags Character vector. Optional tags for the post.
#' @param categories Character vector. Optional categories for the post.
#'
#' @return Invisibly returns the path to the created post directory.
#'
#' @examples
#' \dontrun{
#' create_post("My New Post", slug = "my-new-post")
#' create_post(
#'   title = "Advanced Quarto Tips",
#'   slug = "quarto-tips",
#'   tags = c("quarto", "tips"),
#'   categories = c("tutorial")
#' )
#' }
#'
#' @export
create_post <- function(title, slug, date = Sys.Date(), 
                        tags = character(0), categories = character(0)) {
  
  # Format date if it's a Date object
  if (inherits(date, "Date")) {
    date <- format(date, "%Y-%m-%d")
  }
  
  # Create post directory
  post_dir <- file.path("posts", sprintf("%s-%s", date, slug))
  dir.create(post_dir, recursive = TRUE, showWarnings = FALSE)
  
  # Format tags and categories as YAML lists
  tags_yaml <- if (length(tags) > 0) {
    paste0("[", paste(sprintf('"%s"', tags), collapse = ", "), "]")
  } else {
    "[]"
  }
  
  categories_yaml <- if (length(categories) > 0) {
    paste0("[", paste(sprintf('"%s"', categories), collapse = ", "), "]")
  } else {
    "[]"
  }
  
  # Create frontmatter
  frontmatter <- sprintf(
    "---\ntitle: \"%s\"\ndate: %s\ncategories: %s\ntags: %s\nsubtitle: \"\"\ndescription: \"\"\n---\n\n",
    title, date, categories_yaml, tags_yaml
  )
  
  # Write index.qmd
  index_file <- file.path(post_dir, "index.qmd")
  writeLines(c(frontmatter, "Your post content here."), index_file)
  
  message(sprintf("✓ Created post at: %s", post_dir))
  invisible(post_dir)
}
