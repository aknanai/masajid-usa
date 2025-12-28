#!/usr/bin/env python3
"""
Cleanup script to remove 'Unknown Masjid' entries from all state JSON files
and update the master index with new counts.
"""

import json
import os
from datetime import datetime

# Paths
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'masajid', 'states')
INDEX_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'masajid', '_index.json')
STATIC_DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'static', 'data', 'masajid')

def clean_state_file(filepath):
    """Remove 'Unknown Masjid' entries from a state file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    original_count = len(data['masajid'])

    # Filter out entries with name = "Unknown Masjid"
    data['masajid'] = [m for m in data['masajid'] if m.get('name', '').strip() != 'Unknown Masjid']

    new_count = len(data['masajid'])
    removed_count = original_count - new_count

    # Update count in the file
    data['count'] = new_count

    # Write back
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return data['state'], new_count, removed_count

def main():
    print("Starting cleanup of 'Unknown Masjid' entries...\n")

    state_counts = {}
    total_removed = 0
    total_count = 0

    # Process each state file
    for filename in sorted(os.listdir(DATA_DIR)):
        if filename.endswith('.json'):
            filepath = os.path.join(DATA_DIR, filename)
            state_name, new_count, removed = clean_state_file(filepath)
            state_counts[state_name] = new_count
            total_removed += removed
            total_count += new_count

            if removed > 0:
                print(f"  {state_name}: Removed {removed} 'Unknown Masjid' entries, {new_count} remaining")
            else:
                print(f"  {state_name}: {new_count} masajid (no changes)")

    # Filter out states with 0 masajid
    state_counts = {k: v for k, v in state_counts.items() if v > 0}

    # Update master index
    index_data = {
        "total_count": total_count,
        "state_counts": dict(sorted(state_counts.items())),
        "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    }

    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        json.dump(index_data, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*50}")
    print(f"SUMMARY")
    print(f"{'='*50}")
    print(f"Total 'Unknown Masjid' entries removed: {total_removed}")
    print(f"Total masajid remaining: {total_count}")
    print(f"States with masajid: {len(state_counts)}")
    print(f"\nUpdated _index.json")

    # Copy to static folder
    if os.path.exists(STATIC_DATA_DIR):
        print(f"\nCopying cleaned data to static folder...")

        # Copy index
        static_index = os.path.join(STATIC_DATA_DIR, '_index.json')
        with open(static_index, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, indent=2, ensure_ascii=False)

        # Copy state files
        static_states_dir = os.path.join(STATIC_DATA_DIR, 'states')
        os.makedirs(static_states_dir, exist_ok=True)

        for filename in os.listdir(DATA_DIR):
            if filename.endswith('.json'):
                src = os.path.join(DATA_DIR, filename)
                dst = os.path.join(static_states_dir, filename)
                with open(src, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                with open(dst, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

        print("Done!")

if __name__ == '__main__':
    main()
