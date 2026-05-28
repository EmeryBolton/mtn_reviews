import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / 'data' / 'ski_reviews.db'


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS resorts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            state       TEXT,
            country     TEXT NOT NULL DEFAULT 'USA',
            vertical_ft TEXT,
            acres       TEXT,
            avg_snow_in TEXT,
            owner       TEXT,
            op_class    TEXT,
            UNIQUE(name, state, country)
        );

        CREATE TABLE IF NOT EXISTS place_ids (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            resort_id       INTEGER NOT NULL REFERENCES resorts(id),
            platform        TEXT NOT NULL CHECK(platform IN ('google','tripadvisor')),
            platform_id     TEXT NOT NULL,
            place_name      TEXT,
            address         TEXT,
            latitude        REAL,
            longitude       REAL,
            UNIQUE(platform, platform_id)
        );

        CREATE TABLE IF NOT EXISTS collection_runs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            resort_id   INTEGER NOT NULL REFERENCES resorts(id),
            platform    TEXT NOT NULL,
            run_at      TEXT NOT NULL DEFAULT (datetime('now')),
            rating      REAL,
            total_reviews INTEGER,
            status      TEXT DEFAULT 'ok'
        );

        CREATE TABLE IF NOT EXISTS reviews (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            resort_id       INTEGER NOT NULL REFERENCES resorts(id),
            platform        TEXT NOT NULL,
            review_id       TEXT,
            author          TEXT,
            rating          INTEGER,
            review_date     TEXT,
            text            TEXT,
            language        TEXT,
            collected_at    TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(platform, review_id)
        );

        CREATE INDEX IF NOT EXISTS idx_reviews_resort ON reviews(resort_id, platform);
        CREATE INDEX IF NOT EXISTS idx_runs_resort ON collection_runs(resort_id, platform, run_at);
    """)
    conn.commit()
    conn.close()


def load_resorts_from_csv(csv_path: Path):
    """Seed resorts table from our existing POI CSV."""
    import csv
    conn = get_conn()
    inserted = 0
    with open(csv_path, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO resorts
                        (name, state, country, vertical_ft, acres, avg_snow_in, owner, op_class)
                    VALUES (?,?,?,?,?,?,?,?)
                """, (
                    row['resort_name'], row['state'], row.get('country', 'USA'),
                    row.get('vertical_drop_ft'), row.get('skiable_acres'),
                    row.get('avg_annual_snow_in'), row.get('owner'), row.get('operating_class'),
                ))
                if conn.execute("SELECT changes()").fetchone()[0]:
                    inserted += 1
            except Exception as e:
                print(f"Skipping {row.get('resort_name')}: {e}")
    conn.commit()
    conn.close()
    return inserted


def get_resorts_due(platform: str, days_since: int = 30):
    """Return resorts not collected on this platform within the last N days."""
    conn = get_conn()
    rows = conn.execute("""
        SELECT r.id, r.name, r.state, r.country
        FROM resorts r
        WHERE NOT EXISTS (
            SELECT 1 FROM collection_runs cr
            WHERE cr.resort_id = r.id
              AND cr.platform = ?
              AND cr.run_at > datetime('now', ? || ' days')
        )
        ORDER BY r.state, r.name
    """, (platform, f'-{days_since}')).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_place_id(resort_id, platform, platform_id, place_name=None,
                  address=None, lat=None, lng=None):
    conn = get_conn()
    conn.execute("""
        INSERT OR REPLACE INTO place_ids
            (resort_id, platform, platform_id, place_name, address, latitude, longitude)
        VALUES (?,?,?,?,?,?,?)
    """, (resort_id, platform, platform_id, place_name, address, lat, lng))
    conn.commit()
    conn.close()


def save_run(resort_id, platform, rating, total_reviews, status='ok'):
    conn = get_conn()
    conn.execute("""
        INSERT INTO collection_runs (resort_id, platform, rating, total_reviews, status)
        VALUES (?,?,?,?,?)
    """, (resort_id, platform, rating, total_reviews, status))
    conn.commit()
    conn.close()


def save_reviews(resort_id, platform, reviews: list[dict]):
    conn = get_conn()
    saved = 0
    for r in reviews:
        try:
            conn.execute("""
                INSERT OR IGNORE INTO reviews
                    (resort_id, platform, review_id, author, rating,
                     review_date, text, language)
                VALUES (?,?,?,?,?,?,?,?)
            """, (
                resort_id, platform,
                r.get('review_id'), r.get('author'),
                r.get('rating'), r.get('date'),
                r.get('text'), r.get('language'),
            ))
            if conn.execute("SELECT changes()").fetchone()[0]:
                saved += 1
        except Exception:
            pass
    conn.commit()
    conn.close()
    return saved
