#!/usr/bin/env python3
import os
import subprocess
import re

def main():
    workspace = "/home/robin/github/robinlovelace/robinlovelace.net"
    artifacts_dir = "/home/robin/.gemini/antigravity/brain/6b0bfeb4-db80-47e5-b402-bdb23262ab07"
    screenshots_dir = os.path.join(artifacts_dir, "screenshots")
    os.makedirs(screenshots_dir, exist_ok=True)

    # File paths
    index_html = os.path.join(workspace, "_site/index.html")
    blog_html = os.path.join(workspace, "_site/posts/index.html")

    # Outputs
    home_light_out = os.path.join(screenshots_dir, "home_after_bio_light.png")
    home_dark_out = os.path.join(screenshots_dir, "home_after_bio_dark.png")
    blog_grid_out = os.path.join(screenshots_dir, "blog_after_grid.png")

    # 1. Take home page light mode screenshot
    print("Capturing homepage light mode...")
    cmd_light = [
        "google-chrome", "--headless", "--disable-gpu",
        f"--screenshot={home_light_out}", "--window-size=1280,1200",
        f"file://{index_html}"
    ]
    subprocess.run(cmd_light, check=True)

    # 2. Take blog grid screenshot
    print("Capturing blog grid layout...")
    cmd_blog = [
        "google-chrome", "--headless", "--disable-gpu",
        f"--screenshot={blog_grid_out}", "--window-size=1280,1200",
        f"file://{blog_html}"
    ]
    subprocess.run(cmd_blog, check=True)

    # 3. Create dark mode HTML version
    print("Creating temporary dark mode homepage...")
    with open(index_html, "r", encoding="utf-8") as f:
        content = f.read()

    # Replace body class
    content = content.replace(
        '<body class="nav-fixed landing-page fullcontent quarto-light">',
        '<body class="nav-fixed landing-page fullcontent quarto-dark">'
    )

    # Swap stylesheets for syntax highlighting and bootstrap
    # Find stylesheet link tags and swap rel/disabled or just activate the dark ones
    # A robust way is to swap the files
    # quarto-syntax-highlighting-9fa6dbbe6219e357c3a17d5a2c09c803.css -> light
    # quarto-syntax-highlighting-dark-d2800b5aef52857891e752670e942548.css -> dark
    # bootstrap-524ccf6443f4535991de58515f95e770.min.css -> light
    # bootstrap-dark-178336666853bdbfaa198fab2a57dc20.min.css -> dark
    
    # We can just replace the light CSS files with their dark counterparts in the HTML source:
    content = re.sub(
        r'quarto-syntax-highlighting-[a-f0-9]+\.css',
        'quarto-syntax-highlighting-dark-d2800b5aef52857891e752670e942548.css',
        content
    )
    content = re.sub(
        r'bootstrap-[a-f0-9]+\.min\.css',
        'bootstrap-dark-178336666853bdbfaa198fab2a57dc20.min.css',
        content
    )

    # Write temp file
    temp_dark_html = os.path.join(workspace, "_site/index_dark_temp.html")
    with open(temp_dark_html, "w", encoding="utf-8") as f:
        f.write(content)

    # Take dark mode screenshot
    print("Capturing homepage dark mode...")
    cmd_dark = [
        "google-chrome", "--headless", "--disable-gpu",
        f"--screenshot={home_dark_out}", "--window-size=1280,1200",
        f"file://{temp_dark_html}"
    ]
    subprocess.run(cmd_dark, check=True)

    # Cleanup temp file
    if os.path.exists(temp_dark_html):
        os.remove(temp_dark_html)

    print("Screenshots captured successfully!")

if __name__ == "__main__":
    main()
