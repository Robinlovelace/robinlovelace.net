#!/usr/bin/env python3
import os
import sys

def main():
    redirects_file = "_redirects"
    site_dir = "_site"

    if not os.path.exists(redirects_file):
        print(f"Error: {redirects_file} not found.")
        sys.exit(1)

    if not os.path.exists(site_dir):
        print(f"Error: Output directory {site_dir} not found. Ensure you run this after rendering the site.")
        sys.exit(1)

    count = 0
    with open(redirects_file, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split()
            if len(parts) >= 2:
                src, dst = parts[0], parts[1]
                
                # Skip wildcard or splat rules (like * or :splat)
                if "*" in src or ":" in src:
                    print(f"Line {line_num}: Skipping wildcard redirect '{src} -> {dst}'")
                    continue

                src_clean = src.strip("/")
                if not src_clean:
                    continue

                # Normalize target URL/path
                dst_url = dst
                if not dst.startswith(("http://", "https://")):
                    dst_url = "/" + dst.strip("/")
                    # If it's a directory path and doesn't end with a slash or extension, add one
                    if not dst_url.endswith("/") and not os.path.splitext(dst_url)[1]:
                        dst_url += "/"

                # Determine target file path
                if src.endswith(".html") or src_clean.endswith(".html"):
                    target_file = os.path.join(site_dir, src_clean)
                    os.makedirs(os.path.dirname(target_file), exist_ok=True)
                else:
                    target_dir = os.path.join(site_dir, src_clean)
                    os.makedirs(target_dir, exist_ok=True)
                    target_file = os.path.join(target_dir, "index.html")

                # Generate the meta refresh redirect page
                try:
                    with open(target_file, "w", encoding="utf-8") as out:
                        out.write(f'''<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Redirecting...</title>
  <meta http-equiv="refresh" content="0; url={dst_url}">
  <link rel="canonical" href="{dst_url}">
</head>
<body>
  <p>Redirecting to <a href="{dst_url}">{dst_url}</a>...</p>
</body>
</html>
''')
                    count += 1
                except Exception as e:
                    print(f"Line {line_num}: Failed to write redirect file at '{target_file}': {e}")

    print(f"Successfully generated {count} static HTML redirect stubs under {site_dir}/")

if __name__ == "__main__":
    main()
