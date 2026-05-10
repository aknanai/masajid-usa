#!/usr/bin/env python3
"""
Enhanced masajid data fetcher using multiple OpenStreetMap queries.

Uses 3 strategies to find more masajid than the basic query:
  1. religion=muslim (original query)
  2. building=mosque (catches untagged mosque buildings)
  3. Name-based search for "Masjid", "Mosque", "Islamic Center", "Muslim Center"

Results are deduplicated and merged with existing data.
"""
import json
import os
import time
import sys
from pathlib import Path
from datetime import datetime

import requests

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# US States with bounding boxes (south, west, north, east)
US_STATES = {
    "alabama": (30.2, -88.5, 35.0, -84.9),
    "alaska": (51.2, -179.1, 71.4, -129.9),
    "arizona": (31.3, -114.8, 37.0, -109.0),
    "arkansas": (33.0, -94.6, 36.5, -89.6),
    "california": (32.5, -124.4, 42.0, -114.1),
    "colorado": (37.0, -109.1, 41.0, -102.0),
    "connecticut": (40.9, -73.7, 42.1, -71.8),
    "delaware": (38.4, -75.8, 39.8, -75.0),
    "florida": (24.5, -87.6, 31.0, -80.0),
    "georgia": (30.4, -85.6, 35.0, -80.8),
    "hawaii": (18.9, -160.2, 22.2, -154.8),
    "idaho": (42.0, -117.2, 49.0, -111.0),
    "illinois": (36.9, -91.5, 42.5, -87.5),
    "indiana": (37.8, -88.1, 41.8, -84.8),
    "iowa": (40.4, -96.6, 43.5, -90.1),
    "kansas": (37.0, -102.1, 40.0, -94.6),
    "kentucky": (36.5, -89.6, 39.1, -82.0),
    "louisiana": (28.9, -94.0, 33.0, -89.0),
    "maine": (43.0, -71.1, 47.5, -66.9),
    "maryland": (37.9, -79.5, 39.7, -75.0),
    "massachusetts": (41.2, -73.5, 42.9, -70.0),
    "michigan": (41.7, -90.4, 48.2, -82.4),
    "minnesota": (43.5, -97.2, 49.4, -89.5),
    "mississippi": (30.2, -91.7, 35.0, -88.1),
    "missouri": (36.0, -95.8, 40.6, -89.1),
    "montana": (44.4, -116.0, 49.0, -104.0),
    "nebraska": (40.0, -104.1, 43.0, -95.3),
    "nevada": (35.0, -120.0, 42.0, -114.0),
    "new_hampshire": (42.7, -72.6, 45.3, -70.7),
    "new_jersey": (38.9, -75.6, 41.4, -73.9),
    "new_mexico": (31.3, -109.1, 37.0, -103.0),
    "new_york": (40.5, -79.8, 45.0, -71.9),
    "north_carolina": (33.8, -84.3, 36.6, -75.5),
    "north_dakota": (45.9, -104.0, 49.0, -96.6),
    "ohio": (38.4, -84.8, 42.0, -80.5),
    "oklahoma": (33.6, -103.0, 37.0, -94.4),
    "oregon": (42.0, -124.6, 46.3, -116.5),
    "pennsylvania": (39.7, -80.5, 42.3, -74.7),
    "rhode_island": (41.1, -71.9, 42.0, -71.1),
    "south_carolina": (32.0, -83.4, 35.2, -78.5),
    "south_dakota": (42.5, -104.1, 46.0, -96.4),
    "tennessee": (35.0, -90.3, 36.7, -81.6),
    "texas": (25.8, -106.6, 36.5, -93.5),
    "utah": (37.0, -114.1, 42.0, -109.0),
    "vermont": (42.7, -73.4, 45.0, -71.5),
    "virginia": (36.5, -83.7, 39.5, -75.2),
    "washington": (45.5, -124.8, 49.0, -116.9),
    "west_virginia": (37.2, -82.6, 40.6, -77.7),
    "wisconsin": (42.5, -92.9, 47.1, -86.8),
    "wyoming": (41.0, -111.1, 45.0, -104.1),
    "district_of_columbia": (38.8, -77.1, 39.0, -76.9),
}


def build_religion_query(bbox):
    """Query 1: religion=muslim (original query)"""
    s, w, n, e = bbox
    return f"""
    [out:json][timeout:120];
    (
      node["amenity"="place_of_worship"]["religion"="muslim"]({s},{w},{n},{e});
      way["amenity"="place_of_worship"]["religion"="muslim"]({s},{w},{n},{e});
      relation["amenity"="place_of_worship"]["religion"="muslim"]({s},{w},{n},{e});
    );
    out center tags;
    """


def build_building_query(bbox):
    """Query 2: building=mosque (catches untagged mosque buildings)"""
    s, w, n, e = bbox
    return f"""
    [out:json][timeout:120];
    (
      node["building"="mosque"]({s},{w},{n},{e});
      way["building"="mosque"]({s},{w},{n},{e});
      relation["building"="mosque"]({s},{w},{n},{e});
    );
    out center tags;
    """


def build_name_queries(bbox):
    """Query 3: name-based search — multiple separate queries (Overpass regex has length limits)"""
    s, w, n, e = bbox
    keywords = ["Mosque", "Masjid", "Islamic", "Muslim"]
    queries = []
    for kw in keywords:
        q = f"""
        [out:json][timeout:60];
        (
          node["amenity"="place_of_worship"]["name"~"{kw}", i]({s},{w},{n},{e});
          way["amenity"="place_of_worship"]["name"~"{kw}", i]({s},{w},{n},{e});
          relation["amenity"="place_of_worship"]["name"~"{kw}", i]({s},{w},{n},{e});
        );
        out center tags;
        """
        queries.append((kw, q))
    return queries


def run_query(query, label, retries=3):
    """Run an Overpass query with retry logic."""
    headers = {
        "User-Agent": "MasajidUSA/1.0 (data enrichment for masjid directory; https://github.com/aknanai/masajid-usa)"
    }
    for attempt in range(retries):
        try:
            resp = requests.post(OVERPASS_URL, data={"data": query}, headers=headers, timeout=180)
            resp.raise_for_status()
            data = resp.json()
            print(f"    {label}: {len(data.get('elements', []))} raw results")
            return data.get("elements", [])
        except requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                wait = (attempt + 1) * 10
                print(f"    {label} retry {attempt+1}/{retries} in {wait}s: {e}")
                time.sleep(wait)
            else:
                print(f"    {label} FAILED: {e}")
                return []


def parse_element(element):
    """Parse an OSM element into our standard format."""
    tags = element.get("tags", {})
    typ = element["type"]

    if typ == "node":
        lat = element.get("lat")
        lon = element.get("lon")
    else:
        center = element.get("center", {})
        lat = center.get("lat")
        lon = center.get("lon")

    if not lat or not lon:
        return None

    name = tags.get("name", tags.get("name:en", tags.get("name:ar", "")))
    if not name:
        return None

    house_number = tags.get("addr:housenumber", "")
    street = tags.get("addr:street", "")
    if house_number and street:
        full_street = f"{house_number} {street}"
    elif street:
        full_street = street
    else:
        full_street = tags.get("addr:full", "")

    return {
        "id": f"{typ}_{element['id']}",
        "name": name,
        "address": {
            "street": full_street,
            "city": tags.get("addr:city", ""),
            "state": tags.get("addr:state", ""),
            "zip": tags.get("addr:postcode", ""),
            "full": tags.get("addr:full", ""),
        },
        "phone": tags.get("phone", tags.get("contact:phone", "")),
        "website": tags.get("website", tags.get("contact:website", "")),
        "email": tags.get("email", tags.get("contact:email", "")),
        "coordinates": {"lat": lat, "lon": lon},
        "denomination": tags.get("denomination", ""),
        "opening_hours": tags.get("opening_hours", ""),
        "osm_type": typ,
        "osm_id": element["id"],
    }


def fetch_state(state_name, bbox):
    """Fetch masajid for a state using all 3 query strategies."""
    display = state_name.replace("_", " ").title()
    print(f"\n📌 {display}")

    # Run all queries
    r1 = run_query(build_religion_query(bbox), "religion=muslim")
    time.sleep(2)
    r2 = run_query(build_building_query(bbox), "building=mosque")
    time.sleep(2)

    # Name-based queries (multiple)
    all_name_results = []
    for kw, q in build_name_queries(bbox):
        r = run_query(q, f"name~{kw}")
        all_name_results.extend(r)
        time.sleep(1)
    # Deduplicate name results (same element could match multiple keywords)
    seen_in_name = set()
    r3 = []
    for el in all_name_results:
        eid = f"{el['type']}_{el['id']}"
        if eid not in seen_in_name:
            seen_in_name.add(eid)
            r3.append(el)
    print(f"    name-based (merged): {len(r3)} unique results")

    # Merge & deduplicate: keep track of seen OSM IDs and coordinates
    seen_ids = set()
    seen_coords = set()
    all_masajid = []

    for elements, source in [(r1, "q1"), (r2, "q2"), (r3, "q3")]:
        for el in elements:
            parsed = parse_element(el)
            if not parsed:
                continue

            # Dedup by OSM ID
            if parsed["id"] in seen_ids:
                continue
            seen_ids.add(parsed["id"])

            # Dedup by coordinate proximity (round to 4 decimal places ~11m)
            coord_key = (round(parsed["coordinates"]["lat"], 4), round(parsed["coordinates"]["lon"], 4))
            if coord_key in seen_coords:
                continue
            seen_coords.add(coord_key)

            # Attach state if missing
            if not parsed["address"]["state"]:
                parsed["address"]["state"] = display

            all_masajid.append(parsed)

    print(f"  ✅ Total unique: {len(all_masajid)} masajid")
    return all_masajid


def save_state(state_name, masajid, output_dir):
    """Save masajid data for a state."""
    display = state_name.replace("_", " ").title()
    out_path = output_dir / f"{state_name}.json"

    data = {
        "state": display,
        "count": len(masajid),
        "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "masajid": masajid,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"    Saved: {out_path}")


def create_master_index(states_dir, output_dir):
    """Create master index from all state files."""
    all_masajid = []
    state_counts = {}

    for state_file in sorted(states_dir.glob("*.json")):
        with open(state_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            state_counts[data["state"]] = data["count"]
            all_masajid.extend(data["masajid"])

    master = {
        "total_count": len(all_masajid),
        "state_counts": state_counts,
        "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
    }

    index_path = output_dir / "_index.json"
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(master, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}")
    print(f"📊 MASTER INDEX: {len(all_masajid)} masajid across {len(state_counts)} states")
    print(f"{'='*60}")
    return master


def sync_to_static():
    """Copy data from data/ to static/ for Hugo build."""
    import shutil
    src = Path(__file__).parent.parent / "data" / "masajid"
    dst = Path(__file__).parent.parent / "static" / "data" / "masajid"

    dst.mkdir(parents=True, exist_ok=True)
    (dst / "states").mkdir(parents=True, exist_ok=True)

    # Copy index
    shutil.copy2(src / "_index.json", dst / "_index.json")

    # Copy all state files
    for f in (src / "states").glob("*.json"):
        shutil.copy2(f, dst / "states" / f.name)

    print(f"\n📋 Synced {len(list((src/'states').glob('*.json')))} state files to static/")
    print(f"   (These will be included in the next Hugo build)")


def refresh_all(fresh=False):
    """Fetch/refresh all states."""
    script_dir = Path(__file__).parent.parent
    data_dir = script_dir / "data" / "masajid"
    states_dir = data_dir / "states"
    states_dir.mkdir(parents=True, exist_ok=True)

    total = 0
    for state_name, bbox in US_STATES.items():
        state_file = states_dir / f"{state_name}.json"

        if state_file.exists() and not fresh:
            # Quick re-count without re-fetching
            with open(state_file, "r") as f:
                existing = json.load(f)
            total += existing.get("count", 0)
            display = state_name.replace("_", " ").title()
            print(f"📌 {display}: {existing.get('count', 0)} (cached)")
            continue

        masajid = fetch_state(state_name, bbox)
        if masajid:
            save_state(state_name, masajid, states_dir)
            total += len(masajid)
            time.sleep(3)  # Rate limit for Overpass API
        else:
            print(f"  ⚠️ No results for {state_name}")

    print(f"\n{'='*60}")
    print(f"✅ TOTAL: {total} masajid across {len(US_STATES)} states")

    # Create index
    master = create_master_index(states_dir, data_dir)

    # Sync to static/
    sync_to_static()

    print(f"\n🎉 Done! Next step: regenerate Hugo pages with:")
    print(f"   python3 scripts/generate_pages.py")
    print(f"   Then: git add -A && git commit -m 'update masajid data' && git push")


if __name__ == "__main__":
    fresh = "--fresh" in sys.argv
    single = None
    for arg in sys.argv[1:]:
        if arg.startswith("--state="):
            single = arg.split("=", 1)[1].lower().replace(" ", "_").replace("-", "_")

    if single:
        if single not in US_STATES:
            print(f"Unknown state: {single}")
            sys.exit(1)
        masajid = fetch_state(single, US_STATES[single])
        if masajid:
            script_dir = Path(__file__).parent.parent
            states_dir = script_dir / "data" / "masajid" / "states"
            states_dir.mkdir(parents=True, exist_ok=True)
            save_state(single, masajid, states_dir)
            print(f"\n✅ {single}: {len(masajid)} masajid")
    else:
        refresh_all(fresh=fresh)
