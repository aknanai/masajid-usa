#!/usr/bin/env python3
"""
Create translated content files for all state pages.
Hugo requires language-specific content files for multilingual sites.
Since our state data is the same (just UI translation via i18n),
we create minimal translation files that reference the same data.
"""

import os
from pathlib import Path

# Languages to create translations for
LANGUAGES = ['ar', 'ur', 'es']

def create_state_translations():
    """Create translation files for all state pages."""

    content_dir = Path(__file__).parent.parent / 'content' / 'states'

    if not content_dir.exists():
        print(f"Content directory not found: {content_dir}")
        return

    count = 0

    # Iterate through all state directories
    for state_dir in content_dir.iterdir():
        if not state_dir.is_dir():
            continue

        # Skip if it's not a state directory (e.g., _index.md)
        index_file = state_dir / 'index.md'
        if not index_file.exists():
            continue

        # Read the original index.md to get front matter
        with open(index_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Create translation files for each language
        for lang in LANGUAGES:
            lang_file = state_dir / f'index.{lang}.md'

            # Write the same content (front matter) for each language
            # Hugo will use i18n for UI translations
            with open(lang_file, 'w', encoding='utf-8') as f:
                f.write(content)

            count += 1

    print(f"Created {count} translation files for {len(LANGUAGES)} languages")

    # Also create translations for _index.md (states list page)
    states_index = content_dir / '_index.md'
    if states_index.exists():
        with open(states_index, 'r', encoding='utf-8') as f:
            content = f.read()

        for lang in LANGUAGES:
            lang_file = content_dir / f'_index.{lang}.md'
            with open(lang_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Created {lang_file.name}")

def create_page_translations():
    """Create translation files for standalone pages."""

    content_dir = Path(__file__).parent.parent / 'content'

    # List of standalone pages to translate
    pages = ['about.md', 'qibla.md', 'favorites.md']

    for page in pages:
        page_path = content_dir / page
        if not page_path.exists():
            continue

        with open(page_path, 'r', encoding='utf-8') as f:
            content = f.read()

        for lang in LANGUAGES:
            base_name = page.replace('.md', '')
            lang_file = content_dir / f'{base_name}.{lang}.md'
            with open(lang_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Created {lang_file.name}")

if __name__ == '__main__':
    print("Creating state page translations...")
    create_state_translations()

    print("\nCreating standalone page translations...")
    create_page_translations()

    print("\nDone!")
