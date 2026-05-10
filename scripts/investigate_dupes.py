#!/usr/bin/env python3
"""Investigate duplicates in detail."""
import json, glob
from collections import defaultdict

# Build a map of OSM ID -> list of states it appears in
by_id = defaultdict(list)
by_coord = defaultdict(list)
total = 0

for f in sorted(glob.glob('data/masajid/states/*.json')):
    with open(f) as fh:
        data = json.load(fh)
    state = data['state']
    for m in data['masajid']:
        total += 1
        mid = m['id']
        by_id[mid].append((state, m['name']))
        
        lat = round(m.get('coordinates', {}).get('lat', 0), 3)
        lon = round(m.get('coordinates', {}).get('lon', 0), 3)
        by_coord[(lat, lon)].append((state, mid, m['name']))

# Show actual duplicates
dupe_ids = {k: v for k, v in by_id.items() if len(v) > 1}
dupe_coords = {k: v for k, v in by_coord.items() if len(v) > 1}

print(f"Total masajid: {total}")
print(f"Unique OSM IDs: {len(by_id)}")
print(f"Duplicate OSM IDs: {sum(len(v)-1 for v in dupe_ids.values())} entries")
print(f"Unique coordinates: {len(by_coord)}")
print(f"Duplicate coordinates: {sum(len(v)-1 for v in dupe_coords.values())} entries")
print()

if dupe_ids:
    print(f"{'='*70}")
    print(f"CROSS-STATE DUPLICATES (by OSM ID)")
    print(f"{'='*70}")
    for mid, entries in sorted(dupe_ids.items())[:20]:
        states = [e[0] for e in entries]
        names = [e[1] for e in entries]
        print(f"  {mid}")
        print(f"  Name: {names[0]}")
        print(f"  States: {', '.join(states)}")
        print()
    if len(dupe_ids) > 20:
        print(f"... and {len(dupe_ids)-20} more duplicate IDs")
    print()
    
    # Categorize what kind of duplicates
    same_state = 0
    diff_state = 0
    for mid, entries in dupe_ids.items():
        states = set(e[0] for e in entries)
        if len(states) == 1:
            same_state += 1
        else:
            diff_state += 1
    print(f"  Within same state: {same_state}")
    print(f"  Cross-state (border): {diff_state}")
    
    # If there are same-state duplicates, the dedup didn't work properly
    if same_state > 0:
        print(f"\n  ⚠️ {same_state} masajid appear twice in the SAME state!")
        print(f"  This means the dedup within a state is not working properly.")
        for mid, entries in dupe_ids.items():
            states = set(e[0] for e in entries)
            if len(states) == 1:
                print(f"    {mid}: {entries[0][0]} - {entries[0][1]}")
                break
else:
    print("✅ No OSM ID duplicates at all!")
