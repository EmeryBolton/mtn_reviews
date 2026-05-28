"""
Collects Google Places data (place ID, rating, top 5 reviews) using the
official Places API (New). Free within Google's $200/month credit.
"""
import os
import time
import requests

PLACES_BASE = "https://places.googleapis.com/v1"
API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY", "")

FIELD_MASK = ",".join([
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.location",
    "places.rating",
    "places.userRatingCount",
])

DETAILS_MASK = ",".join([
    "id",
    "displayName",
    "formattedAddress",
    "location",
    "rating",
    "userRatingCount",
    "reviews",
])


def search_place(resort_name: str, state: str, country: str = "USA") -> dict | None:
    """Find the best-matching Google Place for a resort."""
    location_hint = f"{state}, {country}" if state else country
    query = f"{resort_name} ski resort {location_hint}"

    resp = requests.post(
        f"{PLACES_BASE}/places:searchText",
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": API_KEY,
            "X-Goog-FieldMask": FIELD_MASK,
        },
        json={"textQuery": query, "maxResultCount": 1},
        timeout=15,
    )
    resp.raise_for_status()
    places = resp.json().get("places", [])
    return places[0] if places else None


def get_place_details(place_id: str) -> dict:
    """Fetch rating + top 5 reviews for a known place ID."""
    resp = requests.get(
        f"{PLACES_BASE}/places/{place_id}",
        headers={
            "X-Goog-Api-Key": API_KEY,
            "X-Goog-FieldMask": DETAILS_MASK,
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def parse_reviews(details: dict) -> list[dict]:
    reviews = []
    for r in details.get("reviews", []):
        reviews.append({
            "review_id": r.get("name", ""),
            "author": r.get("authorAttribution", {}).get("displayName", ""),
            "rating": r.get("rating"),
            "date": r.get("publishTime", ""),
            "text": r.get("text", {}).get("text", ""),
            "language": r.get("text", {}).get("languageCode", ""),
        })
    return reviews


def collect_resort(resort: dict, delay: float = 0.2) -> dict | None:
    """
    Full collection for one resort.
    Returns dict with place metadata + reviews, or None if not found.
    """
    if not API_KEY:
        raise RuntimeError("GOOGLE_PLACES_API_KEY env var not set")

    place = search_place(resort["name"], resort.get("state", ""), resort.get("country", "USA"))
    if not place:
        return None

    time.sleep(delay)

    place_id = place["id"]
    details = get_place_details(place_id)

    return {
        "platform_id": place_id,
        "place_name": details.get("displayName", {}).get("text", ""),
        "address": details.get("formattedAddress", ""),
        "latitude": details.get("location", {}).get("latitude"),
        "longitude": details.get("location", {}).get("longitude"),
        "rating": details.get("rating"),
        "total_reviews": details.get("userRatingCount"),
        "reviews": parse_reviews(details),
    }
