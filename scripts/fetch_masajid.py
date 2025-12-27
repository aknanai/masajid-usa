#!/usr/bin/env python3
"""
Fetch masajid (Islamic places of worship) data from OpenStreetMap using Overpass API.
This script queries for all masajid in the USA and exports data organized by state.
"""

import json
import os
import time
from pathlib import Path
import requests

# Overpass API endpoint
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# US States with their bounding boxes (approx)
# Format: (south, west, north, east)
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


def build_overpass_query(bbox):
    """Build Overpass QL query for masajid in a bounding box."""
    south, west, north, east = bbox
    query = f"""
    [out:json][timeout:120];
    (
      node["amenity"="place_of_worship"]["religion"="muslim"]({south},{west},{north},{east});
      way["amenity"="place_of_worship"]["religion"="muslim"]({south},{west},{north},{east});
      relation["amenity"="place_of_worship"]["religion"="muslim"]({south},{west},{north},{east});
    );
    out center tags;
    """
    return query


def fetch_masajid_for_state(state_name, bbox, retries=3):
    """Fetch masajid data for a single state with retry logic."""
    print(f"Fetching masajid for {state_name.replace('_', ' ').title()}...")

    query = build_overpass_query(bbox)

    for attempt in range(retries):
        try:
            response = requests.post(
                OVERPASS_URL,
                data={"data": query},
                timeout=180
            )
            response.raise_for_status()
            data = response.json()

            masajid = []
            for element in data.get("elements", []):
                masjid = parse_masjid(element, state_name)
                if masjid:
                    masajid.append(masjid)

            print(f"  Found {len(masajid)} masajid in {state_name.replace('_', ' ').title()}")
            return masajid

        except requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                wait_time = (attempt + 1) * 10  # 10, 20, 30 seconds
                print(f"  Retry {attempt + 1}/{retries} after {wait_time}s: {e}")
                time.sleep(wait_time)
            else:
                print(f"  Failed after {retries} attempts: {e}")
                return None  # Return None to indicate failure (vs empty list)


def parse_masjid(element, state_name):
    """Parse OSM element into masjid data structure."""
    tags = element.get("tags", {})

    # Get coordinates
    if element["type"] == "node":
        lat = element.get("lat")
        lon = element.get("lon")
    else:
        # For ways and relations, use center point
        center = element.get("center", {})
        lat = center.get("lat")
        lon = center.get("lon")

    if not lat or not lon:
        return None

    # Extract name
    name = tags.get("name", tags.get("name:en", tags.get("name:ar", "Unknown Masjid")))

    # Extract address components
    address = {
        "street": tags.get("addr:street", tags.get("addr:housenumber", "")),
        "city": tags.get("addr:city", ""),
        "state": tags.get("addr:state", state_name.replace("_", " ").title()),
        "zip": tags.get("addr:postcode", ""),
        "full": tags.get("addr:full", "")
    }

    # Combine house number and street if both exist
    house_number = tags.get("addr:housenumber", "")
    street = tags.get("addr:street", "")
    if house_number and street:
        address["street"] = f"{house_number} {street}"
    elif street:
        address["street"] = street

    return {
        "id": f"{element['type']}_{element['id']}",
        "name": name,
        "address": address,
        "phone": tags.get("phone", tags.get("contact:phone", "")),
        "website": tags.get("website", tags.get("contact:website", "")),
        "email": tags.get("email", tags.get("contact:email", "")),
        "coordinates": {
            "lat": lat,
            "lon": lon
        },
        "denomination": tags.get("denomination", ""),
        "opening_hours": tags.get("opening_hours", ""),
        "osm_type": element["type"],
        "osm_id": element["id"]
    }


def save_state_data(state_name, masajid, output_dir):
    """Save masajid data for a state to JSON file."""
    output_path = output_dir / f"{state_name}.json"

    state_data = {
        "state": state_name.replace("_", " ").title(),
        "count": len(masajid),
        "masajid": masajid
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(state_data, f, indent=2, ensure_ascii=False)

    print(f"  Saved to {output_path}")


def create_master_index(output_dir):
    """Create master index file with all masajid."""
    all_masajid = []
    state_counts = {}

    for state_file in (output_dir / "states").glob("*.json"):
        with open(state_file, "r", encoding="utf-8") as f:
            state_data = json.load(f)
            state_counts[state_data["state"]] = state_data["count"]
            all_masajid.extend(state_data["masajid"])

    master_data = {
        "total_count": len(all_masajid),
        "state_counts": state_counts,
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    }

    with open(output_dir / "_index.json", "w", encoding="utf-8") as f:
        json.dump(master_data, f, indent=2, ensure_ascii=False)

    print(f"\nMaster index created: {len(all_masajid)} total masajid across {len(state_counts)} states")


def main():
    """Main function to fetch all masajid data."""
    # Setup output directory
    script_dir = Path(__file__).parent.parent
    output_dir = script_dir / "data" / "masajid"
    states_dir = output_dir / "states"
    states_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Masajid USA - Data Collection")
    print("Source: OpenStreetMap (Overpass API)")
    print("=" * 60)
    print()

    # Fetch data for each state
    total_count = 0
    failed_states = []
    for state_name, bbox in US_STATES.items():
        # Skip if already have data for this state
        state_file = states_dir / f"{state_name}.json"
        if state_file.exists():
            print(f"Skipping {state_name.replace('_', ' ').title()} (already exists)")
            with open(state_file, "r", encoding="utf-8") as f:
                existing = json.load(f)
                total_count += existing.get("count", 0)
            continue

        masajid = fetch_masajid_for_state(state_name, bbox)
        if masajid is not None and len(masajid) > 0:
            save_state_data(state_name, masajid, states_dir)
            total_count += len(masajid)
        elif masajid is None:
            failed_states.append(state_name)

        # Be nice to the API - longer wait between requests
        time.sleep(5)

    if failed_states:
        print(f"\nFailed states ({len(failed_states)}): {', '.join(failed_states)}")

    # Create master index
    create_master_index(output_dir)

    print()
    print("=" * 60)
    print(f"Data collection complete! Total: {total_count} masajid")
    print("=" * 60)


def fetch_single_state(state_name):
    """Fetch data for a single state (for testing)."""
    if state_name not in US_STATES:
        print(f"Unknown state: {state_name}")
        print(f"Available states: {', '.join(US_STATES.keys())}")
        return

    script_dir = Path(__file__).parent.parent
    output_dir = script_dir / "data" / "masajid"
    states_dir = output_dir / "states"
    states_dir.mkdir(parents=True, exist_ok=True)

    bbox = US_STATES[state_name]
    masajid = fetch_masajid_for_state(state_name, bbox)

    if masajid:
        save_state_data(state_name, masajid, states_dir)
        print(f"\nSuccess! Found {len(masajid)} masajid in {state_name.replace('_', ' ').title()}")
    else:
        print(f"\nNo masajid found or error occurred for {state_name}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # Test with single state
        state = sys.argv[1].lower().replace(" ", "_")
        fetch_single_state(state)
    else:
        # Fetch all states
        main()
