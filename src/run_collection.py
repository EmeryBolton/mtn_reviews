"""
Main collection runner. Supports:
  python run_collection.py --platform google --mode free
      Use Google Places API (free, 5 reviews/resort)

  python run_collection.py --platform google --mode full --limit 100
      Use Outscraper for Google (paid, up to N reviews/resort)

  python run_collection.py --platform tripadvisor --limit 100
      Use Outscraper for TripAdvisor

  python run_collection.py --platform all --limit 100
      Both platforms via Outscraper

  --days N     Only collect resorts not updated in last N days (default 30)
  --dry-run    Print what would be collected without making API calls
  --max N      Stop after N resorts (useful for testing)
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import db
from google_collector import collect_resort as google_free
from outscraper_collector import collect_google_reviews, collect_tripadvisor_reviews

POI_CSV = Path(__file__).parent.parent / 'data' / 'ski_resorts_us_canada_poi.csv'


def run(platform: str, mode: str, reviews_limit: int,
        days: int, dry_run: bool, max_resorts: int):

    # Init DB and seed resorts on first run
    db.init_db()
    seeded = db.load_resorts_from_csv(POI_CSV)
    if seeded:
        print(f"Seeded {seeded} new resorts into database")

    platforms = ['google', 'tripadvisor'] if platform == 'all' else [platform]

    for plat in platforms:
        resorts = db.get_resorts_due(plat, days_since=days)
        print(f"\n{plat.upper()}: {len(resorts)} resorts due for collection")

        if max_resorts:
            resorts = resorts[:max_resorts]
            print(f"  (capped at {max_resorts} for this run)")

        if dry_run:
            for r in resorts:
                print(f"  would collect: {r['name']}, {r['state']}")
            continue

        ok = skipped = errors = new_reviews = 0

        for i, resort in enumerate(resorts, 1):
            label = f"{resort['name']}, {resort['state'] or resort['country']}"
            print(f"  [{i}/{len(resorts)}] {label}", end=" ... ", flush=True)

            try:
                if plat == 'google' and mode == 'free':
                    result = google_free(resort)
                elif plat == 'google':
                    result = collect_google_reviews(resort, reviews_limit)
                else:
                    result = collect_tripadvisor_reviews(resort, reviews_limit)

                if not result:
                    print("not found")
                    db.save_run(resort['id'], plat, None, None, status='not_found')
                    skipped += 1
                    continue

                db.save_place_id(
                    resort['id'], plat,
                    result['platform_id'], result['place_name'],
                    result['address'], result['latitude'], result['longitude'],
                )
                saved = db.save_reviews(resort['id'], plat, result['reviews'])
                db.save_run(resort['id'], plat, result['rating'], result['total_reviews'])

                new_reviews += saved
                ok += 1
                print(f"rating={result['rating']} total={result['total_reviews']} new_reviews={saved}")

            except KeyboardInterrupt:
                print("\nInterrupted.")
                break
            except Exception as e:
                print(f"ERROR: {e}")
                db.save_run(resort['id'], plat, None, None, status=f'error: {e}')
                errors += 1

        print(f"\n  Done — ok={ok} skipped={skipped} errors={errors} new_reviews={new_reviews}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--platform', choices=['google', 'tripadvisor', 'all'],
                        default='google')
    parser.add_argument('--mode', choices=['free', 'full'], default='free',
                        help='free = Google Places API (5 reviews); full = Outscraper (paid)')
    parser.add_argument('--limit', type=int, default=100,
                        help='Max reviews per resort (Outscraper only)')
    parser.add_argument('--days', type=int, default=30,
                        help='Skip resorts collected within this many days')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--max', type=int, default=0,
                        help='Stop after N resorts (0 = no limit)')
    args = parser.parse_args()

    run(
        platform=args.platform,
        mode=args.mode,
        reviews_limit=args.limit,
        days=args.days,
        dry_run=args.dry_run,
        max_resorts=args.max,
    )


if __name__ == '__main__':
    main()
