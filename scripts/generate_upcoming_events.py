import os
import sys
from datetime import datetime, timezone

# Force stdout/stderr to use UTF-8 encoding on Windows to prevent Quarto/Deno preview issues
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

try:
    import yaml
except ImportError:
    yaml = None

def get_event_data(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        # Extract YAML front matter
        if content.startswith('---'):
            end = content.find('---', 3)
            if end != -1:
                try:
                    data = yaml.safe_load(content[3:end])
                    if data and 'date' in data:
                        # Normalize date
                        dt = data['date']
                        if isinstance(dt, str):
                            # Try parsing if it's a string, though YAML loader often parses it
                            try:
                                dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
                            except:
                                pass
                        
                        # Ensure dt is a datetime object
                        if isinstance(dt, datetime):
                            # Ensure timezone aware for comparison
                            if dt.tzinfo is None:
                                dt = dt.replace(tzinfo=timezone.utc)
                            return {
                                'path': file_path,
                                'date': dt,
                                'title': data.get('title', 'Untitled')
                            }
                except Exception as e:
                    print(f"Error parsing {file_path}: {e}")
    return None

def main():
    if yaml is None:
        print("Warning: 'pyyaml' module not found. Run 'pip install pyyaml' to enable upcoming events auto-generation.", file=sys.stderr)
        print("Quarto build will proceed using the existing upcoming-events.yml.", file=sys.stderr)
        return

    events = []
    events_dir = 'events'
    for root, dirs, files in os.walk(events_dir):
        if 'index.qmd' in files:
            file_path = os.path.join(root, 'index.qmd')
            if file_path == os.path.join(events_dir, 'index.qmd'):
                continue
            data = get_event_data(file_path)
            if data:
                events.append(data)

    now = datetime.now(timezone.utc)
    
    future_events = [e for e in events if e['date'] >= now]
    past_events = [e for e in events if e['date'] < now]

    future_events.sort(key=lambda x: x['date'])
    past_events.sort(key=lambda x: x['date'], reverse=True)

    if future_events:
        # Take up to 3 future events
        selected = future_events[:3]
    else:
        # Take up to 3 most recent past events
        selected = past_events[:3]

    # Quarto listing contents can be a list of paths or a YAML file with metadata
    # We need a list of objects with a 'path' property for it to work correctly in some contexts
    output = [{'path': e['path']} for e in selected]
    
    with open('upcoming-events.yml', 'w', encoding='utf-8') as f:
        yaml.dump(output, f)
    
    print(f"Generated upcoming-events.yml with {len(output)} events.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Warning: Failed to generate upcoming-events.yml due to an error: {e}", file=sys.stderr)
        print("Quarto build will proceed using the existing upcoming-events.yml.", file=sys.stderr)
        sys.exit(0)
