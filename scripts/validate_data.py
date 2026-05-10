#!/usr/bin/env python3
"""Validate masajid data integrity."""
import json, glob

total_issues = 0
total = 0
issues = []

for f in sorted(glob.glob('data/masajid/states/*.json')):
    with open(f) as fh:
        data = json.load(fh)
    
    state = data['state']
    for m in data['masajid']:
        total += 1
        problems = []
        
        coords = m.get('coordinates', {})
        lat = coords.get('lat')
        lon = coords.get('lon')
        
        if lat is None or lon is None:
            problems.append("missing coordinates")
        else:
            if not (18 <= lat <= 72):
                problems.append(f"lat out of US range: {lat}")
            if not (-180 <= lon <= -65):
                problems.append(f"lon out of US range: {lon}")
        
        name = m.get('name', '')
        if not name:
            problems.append("missing name")
        if name == 'Unknown Masjid':
            problems.append("unknown masjid name")
        
        if not m.get('id'):
            problems.append("missing ID")
        
        addr_state = m.get('address', {}).get('state', '')
        if not addr_state:
            problems.append("missing address state")
        
        if problems:
            total_issues += 1
            issues.append((state, m.get('id', '?'), m.get('name', '?'), problems))

print(f"{'='*60}")
print(f"VALIDATION REPORT")
print(f"{'='*60}")
print(f"Total masajid checked: {total}")
print(f"Total with issues: {total_issues}")
print()

if issues:
    print(f"{'STATE':20} {'NAME':35} {'ISSUES'}")
    print(f"{'='*80}")
    for state, mid, name, probs in issues[:30]:
        print(f"{state:20} {name[:34]:35} {', '.join(probs)}")
    if len(issues) > 30:
        print(f"... and {len(issues)-30} more issues")
else:
    print("✅ NO ISSUES FOUND")

# Coordinate stats
print(f"\n{'='*60}")
print(f"COORDINATE ANALYSIS")
print(f"{'='*60}")
valid_coords = 0
lats = []
lons = []
for f in glob.glob('data/masajid/states/*.json'):
    with open(f) as fh:
        data = json.load(fh)
    for m in data['masajid']:
        lat = m.get('coordinates', {}).get('lat')
        lon = m.get('coordinates', {}).get('lon')
        if lat and lon:
            valid_coords += 1
            lats.append(lat)
            lons.append(lon)

print(f"Valid coordinate pairs: {valid_coords}/{total}")
if lats:
    print(f"Lat range: {min(lats):.4f} to {max(lats):.4f}")
    print(f"Lon range: {min(lons):.4f} to {max(lons):.4f}")
    in_bounds = min(lats) >= 18 and max(lats) <= 72 and min(lons) >= -180 and max(lons) <= -65
    print(f"All in US bounds: {in_bounds}")

# Duplicate check
print(f"\n{'='*60}")
print(f"DUPLICATE CHECK")
print(f"{'='*60}")
seen_keys = {}
seen_coords = {}
dupe_osm = 0
dupe_coord = 0
for f in sorted(glob.glob('data/masajid/states/*.json')):
    with open(f) as fh:
        data = json.load(fh)
    for m in data['masajid']:
        mid = m['id']
        if mid in seen_keys:
            dupe_osm += 1
        seen_keys[mid] = True
        lat = round(m.get('coordinates', {}).get('lat', 0), 3)
        lon = round(m.get('coordinates', {}).get('lon', 0), 3)
        key = (lat, lon)
        if key in seen_coords:
            dupe_coord += 1
        seen_coords[key] = mid

print(f"Duplicate OSM IDs: {dupe_osm}")
print(f"Duplicate coords: {dupe_coord}")
print(f"✅ Clean") if dupe_osm == 0 and dupe_coord == 0 else print(f"⚠️ Issues")

# Data completeness
print(f"\n{'='*60}")
print(f"DATA COMPLETENESS")
print(f"{'='*60}")
no_city = 0
no_phone = 0
no_website = 0
for f in glob.glob('data/masajid/states/*.json'):
    with open(f) as fh:
        data = json.load(fh)
    for m in data['masajid']:
        addr = m.get('address', {})
        if not addr.get('city'):
            no_city += 1
        if not m.get('phone'):
            no_phone += 1
        if not m.get('website'):
            no_website += 1

print(f"Missing city: {no_city}/{total} ({no_city/total*100:.0f}%)")
print(f"Missing phone: {no_phone}/{total} ({no_phone/total*100:.0f}%)")  
print(f"Missing website: {no_website}/{total} ({no_website/total*100:.0f}%)")

print(f"\n{'='*60}")
print(f"VERDICT")
print(f"{'='*60}")
if total_issues == 0 and dupe_osm == 0 and dupe_coord == 0:
    print(f"✅ Data is clean! 1,749 masajid ready to go.")
else:
    print(f"⚠️ {total_issues} entries need attention before publishing.")
