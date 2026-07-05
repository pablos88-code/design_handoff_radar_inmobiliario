#!/usr/bin/env python3
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / 'properties.db'
DATA_DIR = ROOT / 'data'
PROPERTIES_PATH = DATA_DIR / 'properties.json'
LANDING_PATH = DATA_DIR / 'landing.json'


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def serialize_property(row: sqlite3.Row) -> dict:
    first_seen = row['first_seen_at']
    try:
        first_dt = datetime.fromisoformat(first_seen.replace('Z', '+00:00'))
    except ValueError:
        first_dt = datetime.now(timezone.utc)
    today = datetime.now(timezone.utc).date()
    days_ago = max(0, (today - first_dt.date()).days)
    if row['is_new']:
        days_ago = 0

    return {
        'id': row['id'],
        'source': row['source'],
        'sourceUrl': row['source_url'],
        'type': row['type'],
        'price': row['price'],
        'currency': row['currency'],
        'lat': row['lat'],
        'lng': row['lng'],
        'locationPrecision': row['location_precision'],
        'title': row['title'],
        'address': row['address'],
        'municipality': row['municipality'],
        'ptype': row['ptype'],
        'rooms': row['rooms'],
        'baths': row['baths'],
        'm2': row['m2'],
        'orientation': row['orientation'],
        'ownerKind': row['owner_kind'],
        'photoUrl': row['photo_url'],
        'firstSeenAt': row['first_seen_at'],
        'lastSeenAt': row['last_seen_at'],
        'isNew': bool(row['is_new']),
        'daysAgo': days_ago,
    }


def build_payload() -> dict:
    with get_connection() as conn:
        rows = conn.execute('SELECT * FROM properties ORDER BY first_seen_at DESC, id DESC LIMIT 400').fetchall()
        properties = [serialize_property(row) for row in rows]
        total_count = conn.execute('SELECT COUNT(*) AS c FROM properties').fetchone()['c']
        new_today = conn.execute("SELECT COUNT(*) AS c FROM properties WHERE is_new = 1 OR date(first_seen_at) = date('now')").fetchone()['c']
        particulars = conn.execute("SELECT COUNT(*) AS c FROM properties WHERE owner_kind = 'particular'").fetchone()['c']
        zones = [row['municipality'] for row in conn.execute("SELECT DISTINCT municipality FROM properties WHERE municipality IS NOT NULL AND municipality != '' ORDER BY municipality")]

    return {
        'properties': properties,
        'filteredCount': total_count,
        'totalCount': total_count,
    }, {
        'totalProperties': total_count,
        'newToday': new_today,
        'particulars': particulars,
        'zonesCount': len(zones),
        'zones': zones,
        'generatedAt': datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    properties_payload, landing_payload = build_payload()
    write_json(PROPERTIES_PATH, properties_payload)
    write_json(LANDING_PATH, landing_payload)
    print(f'Wrote {PROPERTIES_PATH} and {LANDING_PATH}')
