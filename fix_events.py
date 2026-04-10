
import os
import re

def fix_yaml(content):
    # Find YAML front matter block
    match = re.search(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    if not match:
        return content
    
    yaml_block = match.group(1)
    
    # 1. Ensure authors: is present exactly once and set to:
    # authors:
    #   - "Robin Lovelace"
    
    # Look for authors: line(s) and any subsequent indented list items (like - admin)
    # This handles both authors: [] and authors: ["Robin Lovelace"] followed by list items
    authors_pattern = r'^authors:.*?(?=\n\S|$)'
    # Use re.MULTILINE to find authors at start of line in yaml_block
    new_authors = 'authors:\n  - "Robin Lovelace"'
    
    if re.search(r'^authors:', yaml_block, re.MULTILINE):
        yaml_block = re.sub(r'^authors:.*?(?=\n[A-Za-z#]|$)', new_authors, yaml_block, flags=re.MULTILINE | re.DOTALL)
    else:
        # If it doesn't exist, append it at the end of yaml_block
        yaml_block += "\n" + new_authors
    
    # Check for multiple authors lines (it says "ensure it's present exactly once")
    # Actually, the sub above might not handle multiple lines if they are separated.
    # Let's clean up any extra authors: lines if they exist.
    all_authors = re.findall(r'^authors:.*?(?=\n[A-Za-z#]|$)', yaml_block, flags=re.MULTILINE | re.DOTALL)
    if len(all_authors) > 1:
        # Keep only the first one (which we already set to Robin Lovelace if it was there)
        # But wait, my sub above might have replaced only the first one.
        # Let's do a simpler approach: remove all authors: blocks and then add one.
        yaml_block = re.sub(r'^authors:.*?(?=\n[A-Za-z#]|$)', '', yaml_block, flags=re.MULTILINE | re.DOTALL)
        yaml_block += "\n" + new_authors
        
    # Let's refine authors cleanup:
    # Remove all authors: lines and their following indented lines
    yaml_block = re.sub(r'^authors:.*?(?=\n[A-Za-z]|$)', '', yaml_block, flags=re.MULTILINE | re.DOTALL)
    # Ensure we don't have empty lines mess
    yaml_block = yaml_block.strip()
    yaml_block += "\n" + new_authors

    # 3. abstract: followed by a string
    # If it's "abstract:" or "abstract: " at end of line, change to "abstract: \"\""
    yaml_block = re.sub(r'^abstract:\s*$', 'abstract: ""', yaml_block, flags=re.MULTILINE)
    
    # 4. publish-date instead of publishDate
    yaml_block = re.sub(r'^publishDate:', 'publish-date:', yaml_block, flags=re.MULTILINE)
    yaml_block = re.sub(r'^publish_date:', 'publish-date:', yaml_block, flags=re.MULTILINE)
    yaml_block = re.sub(r'^publishdate:', 'publish-date:', yaml_block, flags=re.MULTILINE)
    
    # 5. Remove any leftover complex image: objects
    # Check for image: followed by newline and spaces
    # image:
    #   caption: ...
    #   focal_point: ...
    # If it has caption: or focal_point: in its block, remove the whole image block
    
    def remove_complex_image(m):
        block = m.group(0)
        if 'caption:' in block or 'focal_point:' in block:
            return ""
        return block
    
    yaml_block = re.sub(r'^image:.*?(?=\n[A-Za-z]|$)', remove_complex_image, yaml_block, flags=re.MULTILINE | re.DOTALL)
    
    # Final cleanup of double newlines
    yaml_block = re.sub(r'\n\n+', '\n\n', yaml_block)
    
    new_content = "---\n" + yaml_block.strip() + "\n---\n" + content[match.end():]
    return new_content

root_dir = "events"
for dirpath, dirnames, filenames in os.walk(root_dir):
    for filename in filenames:
        if filename == "index.qmd":
            filepath = os.path.join(dirpath, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            new_content = fix_yaml(content)
            
            if new_content != content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"Fixed: {filepath}")
