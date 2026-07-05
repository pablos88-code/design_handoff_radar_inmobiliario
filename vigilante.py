import os
from datetime import datetime, timezone
from typing import Any, Dict, List

from server import get_connection, insert_property, init_db, now_iso
from scripts.sara_alvarez_scraper import fetch_sara_alvarez_ads


def fetch_idealista_ads() -> List[Dict[str, Any]]:
    api_key = os.environ.get("IDEALISTA_API_KEY")
    if api_key:
        print("Idealista API key configured; real integration can be wired here.")
        return []

    return [
        {
            "source": "Idealista",
            "source_url": "https://demo.local/idealista/sanxenxo/1001",
            "type": "venta",
            "price": 410000.0,
            "lat": 42.4795,
            "lng": -8.8565,
            "location_precision": "approx",
            "title": "Piso reformado cerca de Silgar",
            "address": "Calle Progreso, Sanxenxo",
            "municipality": "Sanxenxo",
            "ptype": "Piso",
            "rooms": 2,
            "baths": 2,
            "m2": 95,
            "orientation": "Sureste",
            "owner_kind": "particular",
            "photo_url": "https://picsum.photos/seed/idealista1/640/400",
            "is_new": 1,
        },
        {
            "source": "Idealista",
            "source_url": "https://demo.local/idealista/pontevedra/1002",
            "type": "alquiler",
            "price": 850.0,
            "lat": 42.4352,
            "lng": -8.6479,
            "location_precision": "exact",
            "title": "Apartamento céntrico con terraza",
            "address": "Rúa Michelena, Pontevedra",
            "municipality": "Pontevedra",
            "ptype": "Apartamento",
            "rooms": 2,
            "baths": 1,
            "m2": 78,
            "orientation": "Sur",
            "owner_kind": "particular",
            "photo_url": "https://picsum.photos/seed/idealista2/640/400",
            "is_new": 1,
        },
    ]


def fetch_freire_ads() -> List[Dict[str, Any]]:
    return [
        {
            "source": "Inmobiliaria Freire",
            "source_url": "https://demo.local/freire/bueu/2001",
            "type": "venta",
            "price": None,
            "lat": 42.3251,
            "lng": -8.7860,
            "location_precision": "exact",
            "title": "Casa con vistas al mar en A Banda do Río",
            "address": "A Banda do Río, Bueu",
            "municipality": "Bueu",
            "ptype": "Casa",
            "rooms": 3,
            "baths": 2,
            "m2": 140,
            "orientation": "Sur",
            "owner_kind": "agencia",
            "photo_url": "https://picsum.photos/seed/freire1/640/400",
            "is_new": 1,
        }
    ]


def fetch_agency_ads() -> List[Dict[str, Any]]:
    try:
        return fetch_sara_alvarez_ads()
    except Exception as exc:
        print(f"Failed to fetch Sara Álvarez ads: {exc}")
        return []


def run_vigilante() -> None:
    init_db()
    with get_connection() as conn:
        conn.execute("DELETE FROM properties WHERE source = ?", ("Sara Álvarez Inmobiliaria",))
        candidates = []
        candidates.extend(fetch_idealista_ads())
        candidates.extend(fetch_freire_ads())
        candidates.extend(fetch_agency_ads())

        inserted = 0
        for payload in candidates:
            payload.setdefault("currency", "EUR")
            payload.setdefault("first_seen_at", now_iso())
            payload.setdefault("last_seen_at", now_iso())
            payload.setdefault("is_new", 1)
            if insert_property(conn, payload):
                inserted += 1

        print(f"Vigilante completed at {datetime.now(timezone.utc).isoformat()}")
        print(f"Inserted {inserted} new properties")


if __name__ == "__main__":
    run_vigilante()
