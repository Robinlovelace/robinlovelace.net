import os
import re
import yaml

events_dir = '/home/robin/github/robinlovelace/robinlovelace.net/events'

for root, dirs, files in os.walk(events_dir):
    if 'index.qmd' in files:
        file_path = os.path.join(root, 'index.qmd')
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split front matter and content
        parts = content.split('---\n', 2)
        if len(parts) < 3:
            continue
        
        front_matter_raw = parts[1]
        body = parts[2]
        
        # Rename publishDate to publish-date
        # We use regex to be safe about case and surrounding space
        front_matter_raw = re.sub(r'^publishDate:', 'publish-date:', front_matter_raw, flags=re.MULTILINE)
        
        # Check for image: object
        # We can try to parse it with yaml to be safe, but regex might be easier for this specific structure
        # The structure is:
        # image:
        #   caption: "..."
        #   focal_point: "..."
        #   preview_only: false
        
        # Let's find the image: block
        image_match = re.search(r'^image:\s*\n((\s+.*\n)*)', front_matter_raw, re.MULTILINE)
        if image_match:
            image_block = image_match.group(0)
            image_content = image_match.group(1)
            
            # If it's an object (starts with indentation)
            if image_content.strip() and image_content.startswith(' '):
                # Look for featured image in the same directory
                image_file = None
                for f_name in os.listdir(root):
                    if f_name.startswith('featured.') and f_name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                        image_file = f_name
                        break
                
                if image_file:
                    # Replace the entire image block with a string
                    new_image_line = f"image: {image_file}\n"
                    front_matter_raw = front_matter_raw.replace(image_block, new_image_line)
                else:
                    # Remove the image block
                    front_matter_raw = front_matter_raw.replace(image_block, "")
        
        # Reconstruct the file
        new_content = f"---\n{front_matter_raw}---\n{body}"
        
        if new_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Updated {file_path}")
