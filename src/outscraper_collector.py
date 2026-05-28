"""
Collects reviews via Outscraper for both Google Maps and TripAdvisor.
Requires an Outscraper API key: https://outscraper.com
Pricing: ~$3/1,000 reviews for Google, ~$5/1,000 for TripAdvisor.
"""
import os
import time
from outscraper import ApiClient

API_KEY = os.environ.get("OUTSCRAPER_API_KEY", "")


def _client() -> ApiClient:
    if not API_KEY:
        raise RuntimeError("OUTSCRAPER_API_KEY env var not set")
    return ApiClient(api_key=API_KEY)


def collect_google_reviews(resort: dict, reviews_limit: int = 100,
                            delay: float = 1.0) -> dict | None:
    """
    Fetch Google Maps reviews for a resort via Outscraper.
    Use this instead of google_collector when you need more than 5 reviews.
    """
    client = _client()
    query = f"{resort['name']} ski resort {resort.get('state', '')} {resort.get('country', 'USA')}"

    try:
        results = client.google_maps_reviews(
            [query],
            reviews_limit=reviews_limit,
            language="en",
        )
        time.sleep(delay)
    except Exception as e:
        print(f"  Outscraper Google error for {resort['name']}: {e}")
        return None

    if not results or not results[0]:
        return None

    place = results[0][0]
    reviews = []
    for r in place.get("reviews_data", []):
        reviews.append({
            "review_id": r.get("review_id", ""),
            "author": r.get("author_title", ""),
            "rating": r.get("review_rating"),
            "date": r.get("review_datetime_utc", ""),
            "text": r.get("review_text", ""),
            "language": r.get("review_language", ""),
        })

    return {
        "platform_id": place.get("place_id", ""),
        "place_name": place.get("name", ""),
        "address": place.get("full_address", ""),
        "latitude": place.get("latitude"),
        "longitude": place.get("longitude"),
        "rating": place.get("rating"),
        "total_reviews": place.get("reviews"),
        "reviews": reviews,
    }


def collect_tripadvisor_reviews(resort: dict, reviews_limit: int = 100,
                                 delay: float = 1.0) -> dict | None:
    """
    Fetch TripAdvisor reviews for a resort via Outscraper.
    """
    client = _client()
    query = f"{resort['name']} ski resort {resort.get('state', '')} {resort.get('country', 'USA')}"

    try:
        results = client.tripadvisor_reviews(
            [query],
            reviews_limit=reviews_limit,
            language="en",
        )
        time.sleep(delay)
    except Exception as e:
        print(f"  Outscraper TripAdvisor error for {resort['name']}: {e}")
        return None

    if not results or not results[0]:
        return None

    place = results[0][0]
    reviews = []
    for r in place.get("reviews_data", []):
        reviews.append({
            "review_id": r.get("review_id", ""),
            "author": r.get("author_title", ""),
            "rating": r.get("review_rating"),
            "date": r.get("review_datetime_utc", ""),
            "text": r.get("review_text", ""),
            "language": "",
        })

    return {
        "platform_id": place.get("location_id", place.get("place_id", "")),
        "place_name": place.get("name", ""),
        "address": place.get("address", ""),
        "latitude": place.get("latitude"),
        "longitude": place.get("longitude"),
        "rating": place.get("rating"),
        "total_reviews": place.get("reviews_count"),
        "reviews": reviews,
    }
