"""
For a given orchard, retrieve its latest survey and collect all
tree survey results into an array.
"""

import json
import sys
import urllib.request
import urllib.error

import utm

BASE_URL = "https://api.aerobotics.com/farming"
ORCHARD_ID = 216269  # <-- replace with your orchard ID


def get_headers():
    token = "4c80d904cae3d86b472fd636ef9d78a36faea104c61c7018a3604285d552d5e4"
    if not token:
        print("Error: Set AEROBOTICS_API_TOKEN environment variable", file=sys.stderr)
        sys.exit(1)
    auth = token if token.startswith("Bearer ") else f"Bearer {token}"
    return {"Authorization": auth, "Content-Type": "application/json"}


def api_get(path, params=None):
    url = f"{BASE_URL}{path}"
    if params:
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{url}?{qs}"
    req = urllib.request.Request(url, headers=get_headers())
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def get_latest_survey(orchard_id):
    """Get surveys for an orchard and return the most recent by date."""
    data = api_get("/surveys/", {"orchard_id": orchard_id, "limit": 100})
    surveys = data["results"]
    if not surveys:
        return None
    return max(surveys, key=lambda s: s["date"])


def get_all_tree_surveys(survey_id):
    """Paginate through all tree surveys for a given survey."""
    tree_surveys = []
    offset = 0
    limit = 100
    while True:
        try:
            data = api_get(
                f"/surveys/{survey_id}/tree_surveys/",
                {"limit": limit, "offset": offset},
            )
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(
                    "  Tree surveys not available (survey may use row segments instead).",
                    file=sys.stderr,
                )
                return []
            raise
        tree_surveys.extend(data["results"])
        if data["next"] is None:
            break
        offset += limit
    return tree_surveys


def add_utm_coordinates(tree_surveys):
    """Add utm_easting, utm_northing, utm_zone_number, utm_zone_letter to each tree survey."""
    for tree in tree_surveys:
        lat, lng = tree.get("lat"), tree.get("lng")
        if lat is not None and lng is not None:
            easting, northing, zone_number, zone_letter = utm.from_latlon(float(lat), float(lng))
            tree["utm_easting"] = easting
            tree["utm_northing"] = northing
            tree["utm_zone_number"] = zone_number
            tree["utm_zone_letter"] = zone_letter
        else:
            tree["utm_easting"] = None
            tree["utm_northing"] = None
            tree["utm_zone_number"] = None
            tree["utm_zone_letter"] = None
    return tree_surveys

def main():
    print(f"Fetching latest survey for orchard {ORCHARD_ID}...")
    survey = get_latest_survey(ORCHARD_ID)
    if not survey:
        print("No surveys found for this orchard.", file=sys.stderr)
        sys.exit(1)

    survey_id = survey["id"]
    print(f"Latest survey: {survey_id} (date: {survey['date']})")

    print("Fetching tree surveys...")
    tree_surveys = get_all_tree_surveys(survey_id)
    print(f"Collected {len(tree_surveys)} tree surveys")

    add_utm_coordinates(tree_surveys)

    # tree_surveys is your working array — each item now also has:
    #   utm_easting, utm_northing, utm_zone_number, utm_zone_letter
    if tree_surveys:
        sample = tree_surveys[0]
        print(f"\nSample tree survey keys: {list(sample.keys())}")
        print(json.dumps(sample, indent=2))

    return tree_surveys


if __name__ == "__main__":
    results = main()
