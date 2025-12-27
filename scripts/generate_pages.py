#!/usr/bin/env python3
"""Generate Hugo content pages for each state."""

import json
import os
from pathlib import Path

def main():
    script_dir = Path(__file__).parent.parent
    data_dir = script_dir / "data" / "masajid"
    content_dir = script_dir / "content" / "states"

    # Create content directory
    content_dir.mkdir(parents=True, exist_ok=True)

    # Create states index page
    index_content = """---
title: "Browse States"
---
"""
    with open(content_dir / "_index.md", "w") as f:
        f.write(index_content)

    # Load master index
    with open(data_dir / "_index.json", "r", encoding="utf-8") as f:
        index = json.load(f)

    # Create a page for each state
    for state_name in index["state_counts"].keys():
        # Create URL-friendly slug
        slug = state_name.lower().replace(" ", "-")
        file_slug = state_name.lower().replace(" ", "_")

        # Create state directory and content
        state_dir = content_dir / slug
        state_dir.mkdir(exist_ok=True)

        content = f"""---
title: "{state_name}"
state_name: "{state_name}"
state_slug: "{file_slug}"
---
"""

        with open(state_dir / "index.md", "w") as f:
            f.write(content)

        print(f"Created page for {state_name}")

    print(f"\nGenerated {len(index['state_counts'])} state pages")

if __name__ == "__main__":
    main()
