import csv
import re
import json
from pathlib import Path

data_dir = Path(__file__).parent
raw_file = data_dir / 'ski_resorts_raw.csv'
out_csv = data_dir / 'ski_resorts_us_canada_poi.csv'
out_summary = data_dir / 'poi_summary.md'

resorts = []
current_location = ''

with open(raw_file, newline='', encoding='utf-8-sig') as f:
    reader = csv.reader(f)
    rows = list(reader)

# Data rows start at index 16 (row 17 in 1-based)
for row in rows[16:]:
    if len(row) < 2:
        continue

    location = row[0].strip()
    mountain = row[1].strip()

    if not mountain:
        continue

    if location:
        current_location = location

    # Only US rows (Canada data is on a separate sheet tab)
    if not current_location.startswith('U.S.'):
        continue

    state_match = re.match(r'U\.S\. - (.+)', current_location)
    if not state_match:
        continue
    state = state_match.group(1).strip()

    def col(i):
        return row[i].strip().replace('"', '') if i < len(row) else ''

    resorts.append({
        'country': 'USA',
        'state': state,
        'resort_name': mountain,
        'vertical_drop_ft': col(2).replace(',', ''),
        'skiable_acres': col(3).replace(',', ''),
        'avg_annual_snow_in': col(4),
        'operating_class': col(5),
        'owner': col(6),
        'pass_affiliations': col(7),
        'operated_2324': col(8),
        'operated_2425': col(9),
        'anticipated_2526': col(10),
        'confirmed_2526': col(11),
    })

# Write POI CSV
fieldnames = list(resorts[0].keys())
with open(out_csv, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(resorts)

# Build summary stats
from collections import Counter
by_state = Counter(r['state'] for r in resorts)
total = len(resorts)

lines = [
    '# Ski Resort POI Summary',
    '',
    f'**Source:** ACTIVE U.S. SKI AREAS 2025-26 (gid=454475097)',
    f'**Total resorts:** {total}',
    f'**Countries covered:** USA only (Canada data is on a separate sheet tab — re-export with the Canada gid to add it)',
    '',
    '## Schema',
    '| Field | Description |',
    '|---|---|',
    '| country | Always "USA" in this extract |',
    '| state | U.S. state name |',
    '| resort_name | Mountain / ski area name |',
    '| vertical_drop_ft | Lift-served vertical drop in feet |',
    '| skiable_acres | Lift-served skiable acres |',
    '| avg_annual_snow_in | Average annual snowfall (claimed), inches |',
    '| operating_class | Public/Private, Aerial/Surface |',
    '| owner | Operating company or "Independent" |',
    '| pass_affiliations | Ski pass programs accepted |',
    '| operated_2324 | Operated in 2023-24 season |',
    '| operated_2425 | Operated in 2024-25 season |',
    '| anticipated_2526 | Anticipates operating 2025-26 |',
    '| confirmed_2526 | Confirmed operating 2025-26 |',
    '',
    '## Breakdown by State',
    f'({total} total resorts across {len(by_state)} states)',
    '',
    '| State | Count |',
    '|---|---|',
]
for state, count in sorted(by_state.items()):
    lines.append(f'| {state} | {count} |')

out_summary.write_text('\n'.join(lines), encoding='utf-8')
print(f"Done. {total} resorts written to {out_csv.name}")
print(f"Summary written to {out_summary.name}")
