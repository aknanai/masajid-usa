#!/usr/bin/env python3
"""
Google Places API integration for Masajid USA.

Fetches masajid/Islamic centers from Google Places and merges with existing OSM data.
Deduplicates by name similarity and coordinate proximity.

Usage:
  # Search all states (recommended)
  python3 scripts/fetch_google_places.py --api-key YOUR_KEY
  
  # Search a single state (for testing)
  python3 scripts/fetch_google_places.py --api-key YOUR_KEY --state=california

  # Dry run - show what would be added without saving
  python3 scripts/fetch_google_places.py --api-key YOUR_KEY --dry-run --state=texas
"""
import json
import os
import sys
import time
import re
from pathlib import Path
from datetime import datetime

import requests


# US major cities with their coordinates (for targeted Place searches)
# Each state gets searches from its most populous cities
CITIES = {
    "alabama": [("Birmingham", 33.5186, -86.8104), ("Huntsville", 34.7304, -86.5861), ("Mobile", 30.6954, -88.0399)],
    "alaska": [("Anchorage", 61.2181, -149.9003), ("Fairbanks", 64.8378, -147.7164)],
    "arizona": [("Phoenix", 33.4484, -112.0740), ("Tucson", 32.2226, -110.9747), ("Mesa", 33.4151, -111.8315)],
    "arkansas": [("Little Rock", 34.7465, -92.2896), ("Fayetteville", 36.0626, -94.1574)],
    "california": [("Los Angeles", 34.0522, -118.2437), ("San Francisco", 37.7749, -122.4194), ("San Diego", 32.7157, -117.1611), ("Sacramento", 38.5816, -121.4944), ("San Jose", 37.3382, -121.8863), ("Fresno", 36.7378, -119.7871)],
    "colorado": [("Denver", 39.7392, -104.9903), ("Colorado Springs", 38.8339, -104.8214)],
    "connecticut": [("Hartford", 41.7658, -72.6734), ("New Haven", 41.3083, -72.9281)],
    "delaware": [("Wilmington", 39.7447, -75.5484), ("Dover", 39.1582, -75.5244)],
    "district_of_columbia": [("Washington DC", 38.9072, -77.0369)],
    "florida": [("Miami", 25.7617, -80.1918), ("Orlando", 28.5383, -81.3792), ("Jacksonville", 30.3322, -81.6557), ("Tampa", 27.9506, -82.4572)],
    "georgia": [("Atlanta", 33.7490, -84.3880), ("Augusta", 33.4735, -82.0105)],
    "hawaii": [("Honolulu", 21.3069, -157.8583)],
    "idaho": [("Boise", 43.6150, -116.2023)],
    "illinois": [("Chicago", 41.8781, -87.6298), ("Springfield", 39.7817, -89.6501)],
    "indiana": [("Indianapolis", 39.7684, -86.1581), ("Fort Wayne", 41.0793, -85.1394)],
    "iowa": [("Des Moines", 41.5868, -93.6250), ("Cedar Rapids", 41.9779, -91.6656)],
    "kansas": [("Wichita", 37.6872, -97.3301), ("Kansas City", 39.1140, -94.6275)],
    "kentucky": [("Louisville", 38.2527, -85.7585), ("Lexington", 38.0406, -84.5037)],
    "louisiana": [("New Orleans", 29.9511, -90.0715), ("Baton Rouge", 30.4515, -91.1871)],
    "maine": [("Portland", 43.6615, -70.2553)],
    "maryland": [("Baltimore", 39.2904, -76.6122), ("Silver Spring", 38.9907, -77.0261)],
    "massachusetts": [("Boston", 42.3601, -71.0589), ("Worcester", 42.2626, -71.8023)],
    "michigan": [("Detroit", 42.3314, -83.0458), ("Grand Rapids", 42.9634, -85.6681), ("Dearborn", 42.3223, -83.1763)],
    "minnesota": [("Minneapolis", 44.9778, -93.2650), ("St Paul", 44.9537, -93.0900)],
    "mississippi": [("Jackson", 32.2988, -90.1848)],
    "missouri": [("St Louis", 38.6270, -90.1994), ("Kansas City", 39.0997, -94.5786)],
    "montana": [("Billings", 45.7833, -108.5007)],
    "nebraska": [("Omaha", 41.2565, -95.9345)],
    "nevada": [("Las Vegas", 36.1699, -115.1398), ("Reno", 39.5296, -119.8138)],
    "new_hampshire": [("Manchester", 42.9956, -71.4548)],
    "new_jersey": [("Newark", 40.7357, -74.1724), ("Jersey City", 40.7282, -74.0776), ("Paterson", 40.9168, -74.1718)],
    "new_mexico": [("Albuquerque", 35.0853, -106.6056)],
    "new_york": [("New York City", 40.7128, -74.0060), ("Buffalo", 42.8864, -78.8784), ("Albany", 42.6526, -73.7562), ("Rochester", 43.1566, -77.6088)],
    "north_carolina": [("Charlotte", 35.2271, -80.8431), ("Raleigh", 35.7796, -78.6382)],
    "north_dakota": [("Fargo", 46.8772, -96.7898)],
    "ohio": [("Columbus", 39.9612, -82.9988), ("Cleveland", 41.4993, -81.6944), ("Cincinnati", 39.1031, -84.5120)],
    "oklahoma": [("Oklahoma City", 35.4676, -97.5164), ("Tulsa", 36.1540, -95.9928)],
    "oregon": [("Portland", 45.5152, -122.6784)],
    "pennsylvania": [("Philadelphia", 39.9526, -75.1652), ("Pittsburgh", 40.4406, -79.9959)],
    "rhode_island": [("Providence", 41.8240, -71.4128)],
    "south_carolina": [("Columbia", 34.0007, -81.0348), ("Charleston", 32.7765, -79.9311)],
    "south_dakota": [("Sioux Falls", 43.5446, -96.7311)],
    "tennessee": [("Nashville", 36.1627, -86.7816), ("Memphis", 35.1495, -90.0490)],
    "texas": [("Houston", 29.7604, -95.3698), ("Dallas", 32.7767, -96.7970), ("San Antonio", 29.4241, -98.4936), ("Austin", 30.2672, -97.7431), ("Fort Worth", 32.7555, -97.3308)],
    "utah": [("Salt Lake City", 40.7608, -111.8910)],
    "vermont": [("Burlington", 44.4759, -73.2121)],
    "virginia": [("Richmond", 37.5407, -77.4360), ("Virginia Beach", 36.8529, -75.9780), ("Alexandria", 38.8048, -77.0469)],
    "washington": [("Seattle", 47.6062, -122.3321), ("Spokane", 47.6588, -117.4260)],
    "west_virginia": [("Charleston", 38.3498, -81.6326)],
    "wisconsin": [("Milwaukee", 43.0389, -87.9065), ("Madison", 43.0731, -89.4012)],
    "wyoming": [("Cheyenne", 41.1400, -104.8202)],
}

# Search keywords for Google Places
SEARCH_KEYWORDS = [
    "mosque",
    "masjid",
    "Islamic center",
    "Muslim community center"
]


def normalize_name(name):
    """Normalize a name for comparison."""
    n = name.lower().strip()
    n = re.sub(r'[^a-z0-9\s]', '', n)
    n = re.sub(r'\s+', ' ', n)
    return n.strip()


def name_similarity(name1, name2):
    """Check if two names likely refer to the same place."""
    n1 = normalize_name(name1)
    n2 = normalize_name(name2)
    
    # Direct match
    if n1 == n2:
        return True
    
    # One contains the other
    if n1 in n2 or n2 in n1:
        return True
    
    # Remove common prefixes/suffixes and compare
    prefixes = ['al-', 'al ', 'masjid ', 'masjidul ', 'masjid-al ', 'masjid al ']
    suffixes = [' mosque', ' masjid', ' center', ' centre', ' foundation']
    
    def strip_common(s):
        for p in prefixes:
            if s.startswith(p):
                s = s[len(p):]
                break
        for sf in suffixes:
            if s.endswith(sf):
                s = s[:-len(sf)]
                break
        return s.strip()
    
    s1 = strip_common(n1)
    s2 = strip_common(n2)
    
    if s1 == s2:
        return True
    if len(s1) > 3 and len(s2) > 3 and (s1 in s2 or s2 in s1):
        return True
    
    return False


def is_duplicate(new_place, existing_masajid, coord_threshold=0.02):
    """Check if a Google Places result matches an existing OSM masjid."""
    new_lat = new_place['geometry']['location']['lat']
    new_lng = new_place['geometry']['location']['lng']
    new_name = new_place.get('name', '')
    
    for existing in existing_masajid:
        e_lat = existing['coordinates']['lat']
        e_lng = existing['coordinates']['lon']
        
        # Coordinate proximity check (0.02 ≈ 2km)
        lat_diff = abs(new_lat - e_lat)
        lng_diff = abs(new_lng - e_lng)
        
        if lat_diff < coord_threshold and lng_diff < coord_threshold:
            # Same area - check name similarity
            e_name = existing.get('name', '')
            if name_similarity(new_name, e_name):
                return True
        
        # Very close coordinates (< 100m) — almost certainly same place
        if lat_diff < 0.001 and lng_diff < 0.001:
            return True
    
    return False


def search_city(api_key, city_name, lat, lng, state_name, radius=15000):
    """Search for masajid near a city using Google Places API."""
    all_results = []
    seen_place_ids = set()
    
    for keyword in SEARCH_KEYWORDS:
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        params = {
            "query": f"{keyword} near {city_name}, {state_name}",
            "location": f"{lat},{lng}",
            "radius": radius,
            "key": api_key,
        }
        
        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            
            if data.get("status") != "OK" and data.get("status") != "ZERO_RESULTS":
                if data.get("status") == "OVER_QUERY_LIMIT":
                    print(f"    ⚠️ Rate limited! Waiting 60s...")
                    time.sleep(60)
                    continue
                elif data.get("status") == "INVALID_REQUEST":
                    print(f"    ⚠️ Invalid request for {keyword} in {city_name}")
                    continue
                elif data.get("status") == "REQUEST_DENIED":
                    print(f"    ❌ API request denied! Check your API key.")
                    return all_results
            
            for place in data.get("results", []):
                place_id = place.get("place_id", "")
                if place_id and place_id not in seen_place_ids:
                    seen_place_ids.add(place_id)
                    all_results.append(place)
            
            # Check for pagination
            if "next_page_token" in data:
                time.sleep(2)  # Must wait before using next_page_token
                params["pagetoken"] = data["next_page_token"]
                try:
                    resp2 = requests.get(url, params=params, timeout=15)
                    resp2.raise_for_status()
                    data2 = resp2.json()
                    for place in data2.get("results", []):
                        place_id = place.get("place_id", "")
                        if place_id and place_id not in seen_place_ids:
                            seen_place_ids.add(place_id)
                            all_results.append(place)
                except Exception:
                    pass
            
            time.sleep(0.5)  # Rate limiting between keywords
            
        except requests.exceptions.RequestException as e:
            print(f"    ⚠️ Error: {e}")
            time.sleep(2)
    
    return all_results


def parse_google_place(place, state_name):
    """Convert a Google Places result to our masjid format."""
    name = place.get("name", "Unknown Masjid")
    geometry = place.get("geometry", {})
    location = geometry.get("location", {})
    lat = location.get("lat")
    lng = location.get("lng")
    
    if not lat or not lng:
        return None
    
    # Parse address components
    address_components = place.get("address_components", [])
    addr_parts = {"street_number": "", "route": "", "city": "", "state": "", "zip": ""}
    
    for component in address_components:
        types = component.get("types", [])
        value = component.get("long_name", "")
        if "street_number" in types:
            addr_parts["street_number"] = value
        elif "route" in types:
            addr_parts["route"] = value
        elif "locality" in types or "sublocality" in types:
            addr_parts["city"] = value
        elif "administrative_area_level_1" in types:
            addr_parts["state"] = value
        elif "postal_code" in types:
            addr_parts["zip"] = value
    
    # Build street address
    street = ""
    if addr_parts["street_number"] and addr_parts["route"]:
        street = f"{addr_parts['street_number']} {addr_parts['route']}"
    elif addr_parts["route"]:
        street = addr_parts["route"]
    
    formatted_address = place.get("formatted_address", "")
    
    # Parse phone and website from details (would need Place Details API)
    # For now, just use what text search gives us
    
    return {
        "id": f"google_{place.get('place_id', 'unknown')}",
        "name": name,
        "address": {
            "street": street,
            "city": addr_parts["city"],
            "state": addr_parts["state"] or state_name.title(),
            "zip": addr_parts["zip"],
            "full": formatted_address,
        },
        "phone": "",  # Would require Place Details API
        "website": "",  # Would require Place Details API
        "email": "",
        "coordinates": {"lat": lat, "lon": lng},
        "denomination": "",
        "opening_hours": "",
        "source": "google_places",
        "google_place_id": place.get("place_id", ""),
        "rating": place.get("rating", 0),
        "user_ratings_total": place.get("user_ratings_total", 0),
    }


def fetch_state_from_google(api_key, state_key, existing_masajid, dry_run=False):
    """Fetch masajid for a state from Google Places and merge with existing."""
    state_name = state_key.replace("_", " ").title()
    cities = CITIES.get(state_key, [])
    
    if not cities:
        print(f"\n📌 {state_name} — No cities configured, skipping")
        return [], []
    
    print(f"\n📌 {state_name} ({len(cities)} cities)")
    
    all_results = []
    seen_place_ids = set()
    
    for city_name, lat, lng in cities:
        print(f"  🔍 Searching {city_name}...")
        results = search_city(api_key, city_name, lat, lng, state_name)
        
        # Deduplicate across cities within same state
        new_for_city = 0
        for place in results:
            pid = place.get("place_id", "")
            if pid and pid not in seen_place_ids:
                seen_place_ids.add(pid)
                all_results.append(place)
                new_for_city += 1
        
        print(f"     Found {new_for_city} new (total so far: {len(all_results)})")
        time.sleep(1)  # Rate limiting between cities
    
    # Parse results
    parsed = []
    duplicates = 0
    for place in all_results:
        m = parse_google_place(place, state_name)
        if not m:
            continue
        
        if is_duplicate(place, existing_masajid):
            duplicates += 1
            continue
        
        parsed.append(m)
    
    print(f"  📊 Results: {len(all_results)} raw, {duplicates} OSM duplicates, {len(parsed)} new")
    
    return parsed, all_results


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Fetch masajid data from Google Places")
    parser.add_argument("--api-key", required=True, help="Google Places API key")
    parser.add_argument("--state", help="Single state to fetch (snake_case)")
    parser.add_argument("--dry-run", action="store_true", help="Show results without saving")
    parser.add_argument("--output-dir", help="Output directory (default: data/masajid/states)")
    
    args = parser.parse_args()
    
    script_dir = Path(__file__).parent.parent
    
    # Determine output dir
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = script_dir / "data" / "masajid" / "states"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load existing OSM data for dedup
    existing_masajid = {}
    for f in sorted(output_dir.glob("*.json")):
        with open(f) as fh:
            data = json.load(fh)
        key = Path(f).stem
        existing_masajid[key] = data.get("masajid", [])
    
    print(f"{'='*60}")
    print(f"Google Places Masajid Fetcher")
    print(f"{'='*60}")
    print(f"Existing OSM data: {sum(len(v) for v in existing_masajid.values())} masajid across {len(existing_masajid)} states")
    
    # Determine states to process
    state_keys = [args.state] if args.state else list(CITIES.keys())
    
    total_new = 0
    total_searched = 0
    state_new_counts = {}
    
    for state_key in state_keys:
        state_key = state_key.lower().replace(" ", "_").replace("-", "_")
        if state_key not in CITIES and state_key not in existing_masajid:
            print(f"\n⚠️ Unknown state: {state_key}")
            continue
        
        existing = existing_masajid.get(state_key, [])
        new_masajid, raw_results = fetch_state_from_google(
            args.api_key, state_key, existing, dry_run=args.dry_run
        )
        
        state_name = state_key.replace("_", " ").title()
        state_new_counts[state_name] = len(new_masajid)
        total_new += len(new_masajid)
        total_searched += len(raw_results)
        
        if not args.dry_run and new_masajid:
            # Merge with existing
            all_masajid = existing + new_masajid
            
            state_file = output_dir / f"{state_key}.json"
            
            # Handle states with no existing OSM file (e.g., Montana, ND, NH, SD)
            if state_file.exists():
                with open(state_file) as f:
                    state_data = json.load(f)
            else:
                state_data = {
                    "state": state_name,
                    "count": 0,
                    "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "masajid": []
                }
            
            state_data["masajid"] = all_masajid
            state_data["count"] = len(all_masajid)
            state_data["google_places_added"] = len(new_masajid)
            
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)
            
            print(f"    ✅ Saved: {len(all_masajid)} total ({len(new_masajid)} new from Google)")
        
        # Rate limiting between states
        time.sleep(2)
    
    # Summary
    print(f"\n{'='*60}")
    print(f"GOOGLE PLACES SUMMARY")
    print(f"{'='*60}")
    print(f"States searched: {len(state_keys)}")
    print(f"Raw results fetched: {total_searched}")
    print(f"New masajid found (after OSM dedup): {total_new}")
    
    if args.dry_run:
        print(f"\n💡 This was a DRY RUN — no data was saved.")
        print(f"   Run without --dry-run to save.")
    
    print()
    if total_new > 0 and not args.dry_run:
        print("⚠️ Data saved locally but NOT synced to static/. Run:")
        print("   python3 scripts/cleanup_data.py")
        print("   python3 scripts/generate_pages.py")
        print("   Then: git add -A && git commit && git push")


if __name__ == "__main__":
    main()
