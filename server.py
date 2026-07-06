import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "properties.db"
INDEX_PATH = ROOT / "index.html"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS properties (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                source_url TEXT UNIQUE NOT NULL,
                type TEXT NOT NULL,
                price REAL,
                currency TEXT NOT NULL DEFAULT 'EUR',
                lat REAL NOT NULL,
                lng REAL NOT NULL,
                location_precision TEXT NOT NULL DEFAULT 'exact',
                title TEXT NOT NULL,
                address TEXT NOT NULL,
                municipality TEXT,
                ptype TEXT,
                rooms INTEGER,
                baths INTEGER,
                m2 REAL,
                orientation TEXT,
                owner_kind TEXT NOT NULL,
                photo_url TEXT,
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                is_new INTEGER NOT NULL DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_properties_type ON properties(type);
            CREATE INDEX IF NOT EXISTS idx_properties_owner ON properties(owner_kind);
            CREATE INDEX IF NOT EXISTS idx_properties_source ON properties(source);
            """
        )


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def insert_property(conn: sqlite3.Connection, payload: Dict[str, Any]) -> bool:
    source_url = payload.get("source_url")
    if not source_url:
        raise ValueError("source_url is required")

    existing = conn.execute(
        "SELECT id FROM properties WHERE source_url = ? LIMIT 1",
        (source_url,),
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE properties SET last_seen_at = ?, is_new = 0 WHERE id = ?",
            (now_iso(), existing["id"]),
        )
        return False

    conn.execute(
        """
        INSERT INTO properties (
            source, source_url, type, price, currency, lat, lng, location_precision,
            title, address, municipality, ptype, rooms, baths, m2, orientation,
            owner_kind, photo_url, first_seen_at, last_seen_at, is_new
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload.get("source", "demo"),
            source_url,
            payload.get("type", "venta"),
            payload.get("price"),
            payload.get("currency", "EUR"),
            payload.get("lat"),
            payload.get("lng"),
            payload.get("location_precision", "exact"),
            payload.get("title", "Propiedad"),
            payload.get("address", "Sin dirección"),
            payload.get("municipality", "Galicia"),
            payload.get("ptype", "Piso"),
            payload.get("rooms"),
            payload.get("baths"),
            payload.get("m2"),
            payload.get("orientation"),
            payload.get("owner_kind", "agencia"),
            payload.get("photo_url"),
            payload.get("first_seen_at") or now_iso(),
            payload.get("last_seen_at") or now_iso(),
            int(payload.get("is_new", 0)),
        ),
    )
    return True


SOURCE_URL_DOMAIN_MAP = {
    "Idealista": "https://www.idealista.com/inmueble",
    "Fotocasa": "https://www.fotocasa.es/es/comprar/vivienda",
    "Wallapop": "https://www.wallapop.com/item",
    "Milanuncios": "https://www.milanuncios.com/venta-inmuebles",
    "Inmobiliaria Freire": "https://www.inmobiliariafreire.com/anuncio",
    "Sara Álvarez Inmobiliaria": "https://www.saraalvarezinmobiliaria.com",
}

def normalize_source_url(source_url: str, source: str) -> str:
    if not source_url:
        return source_url
    if "demo.local" not in source_url:
        return source_url
    domain = SOURCE_URL_DOMAIN_MAP.get(source)
    if domain:
        suffix = source_url.split("/", 3)[-1]
        return f"{domain}/{suffix}"
    return source_url.replace("https://demo.local", "https://example.com")


def serialize_property(row: sqlite3.Row) -> Dict[str, Any]:
    first_seen = row["first_seen_at"]
    try:
        first_dt = datetime.fromisoformat(first_seen.replace("Z", "+00:00"))
    except ValueError:
        first_dt = datetime.now(timezone.utc)
    today = datetime.now(timezone.utc).date()
    days_ago = max(0, (today - first_dt.date()).days)
    if row["is_new"]:
        days_ago = 0
    return {
        "id": row["id"],
        "source": row["source"],
        "sourceUrl": normalize_source_url(row["source_url"], row["source"]),
        "type": row["type"],
        "price": row["price"],
        "currency": row["currency"],
        "lat": row["lat"],
        "lng": row["lng"],
        "locationPrecision": row["location_precision"],
        "title": row["title"],
        "address": row["address"],
        "municipality": row["municipality"],
        "ptype": row["ptype"],
        "rooms": row["rooms"],
        "baths": row["baths"],
        "m2": row["m2"],
        "orientation": row["orientation"],
        "ownerKind": row["owner_kind"],
        "photoUrl": row["photo_url"],
        "firstSeenAt": row["first_seen_at"],
        "lastSeenAt": row["last_seen_at"],
        "isNew": bool(row["is_new"]),
        "daysAgo": days_ago,
    }


def seed_demo_data() -> int:
    with get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) AS c FROM properties").fetchone()["c"]
        if count >= 320:
            return count

        conn.execute("DELETE FROM properties")

        zones = [
            {"name": "Pontevedra", "lat": 42.4318, "lng": -8.6446, "n": 80, "spread": 0.017},
            {"name": "Vigo", "lat": 42.2328, "lng": -8.7226, "n": 70, "spread": 0.017},
            {"name": "Sanxenxo", "lat": 42.4790, "lng": -8.8570, "n": 35, "spread": 0.015},
            {"name": "Marín", "lat": 42.3910, "lng": -8.7020, "n": 28, "spread": 0.014},
            {"name": "Poio", "lat": 42.4650, "lng": -8.7270, "n": 24, "spread": 0.013},
            {"name": "Bueu", "lat": 42.3240, "lng": -8.7850, "n": 25, "spread": 0.013},
            {"name": "Cela", "lat": 42.3180, "lng": -8.7620, "n": 18, "spread": 0.012},
            {"name": "Beluso", "lat": 42.3300, "lng": -8.8150, "n": 16, "spread": 0.012},
            {"name": "A Caeira", "lat": 42.4345, "lng": -8.6585, "n": 12, "spread": 0.011},
            {"name": "Marcón", "lat": 42.4180, "lng": -8.6050, "n": 10, "spread": 0.011},
            {"name": "Bora", "lat": 42.4370, "lng": -8.5850, "n": 8, "spread": 0.010},
            {"name": "Xeve", "lat": 42.4750, "lng": -8.6150, "n": 8, "spread": 0.010},
        ]

        ptypes = ["Piso", "Apartamento", "Casa", "Chalet", "Ático", "Estudio", "Adosado"]
        orients = ["Sur", "Norte", "Este", "Oeste", "Sureste", "Suroeste", "Noreste"]
        sources = ["Idealista", "Fotocasa", "Wallapop", "Milanuncios", "Sara Álvarez Inmobiliaria", "Inmobiliaria Freire"]
        streets = [
            "Rúa do Príncipe", "Gran Vía", "Rúa Urzáiz", "Bouzas", "Casco Vello", "Praza da Peregrina",
            "A Ferrería", "Rúa Michelena", "Avenida de Vigo", "Praza de Galicia", "Calle Progreso", "A Banda do Río",
            "Bon de Abaixo", "Meiro", "A Graña", "As Meanes", "Montemogos", "A Caeira", "O Valado", "Adina"
        ]

        seed = 17
        def rnd() -> float:
            nonlocal seed
            seed = (seed * 16807) % 2147483647
            return (seed - 1) / 2147483646

        for zone in zones:
            for idx in range(zone["n"]):
                rent = rnd() < 0.32
                ptype = ptypes[int(rnd() * len(ptypes))]
                rooms = 1 if ptype == "Estudio" else 1 + int(rnd() * 4)
                m2 = 45 + int(rnd() * 180)
                price = 450 + int(rnd() * 14) * 50 if rent else 90000 + int(rnd() * 90) * 5000
                source = sources[int(rnd() * len(sources))]
                owner_kind = "particular" if rnd() < 0.38 else "agencia"
                prop_type = "alquiler" if rent else "venta"
                if source in {"Sara Álvarez Inmobiliaria", "Inmobiliaria Freire"}:
                    prop_type = "venta"
                    price = None
                if owner_kind == "particular" and prop_type == "agencia":
                    prop_type = "venta"
                payload = {
                    "source": source,
                    "source_url": f"https://demo.local/{source.lower().replace(' ', '-')}/{zone['name'].lower().replace(' ', '-')}/{idx + 1000}",
                    "type": "agencia" if source == "Sara Álvarez Inmobiliaria" else prop_type,
                    "price": None if price is None else float(price),
                    "currency": "EUR",
                    "lat": zone["lat"] + (rnd() - 0.5) * (zone.get("spread", 0.045)),
                    "lng": zone["lng"] + (rnd() - 0.5) * (zone.get("spread", 0.045) * 1.33),
                    "location_precision": "exact" if rnd() > 0.2 else "approx",
                    "title": f"{['Luminoso', 'Reformado', 'Amplio', 'Céntrico', 'Acogedor', 'Exterior', 'Con terraza', 'Con garaje'][int(rnd() * 8)]} {ptype.lower()} de {rooms} {'habitación' if rooms == 1 else 'habitaciones'}",
                    "address": f"{streets[int(rnd() * len(streets))]}, {zone['name']}",
                    "municipality": zone["name"],
                    "ptype": ptype,
                    "rooms": rooms,
                    "baths": 1 + int(rnd() * 2),
                    "m2": m2,
                    "orientation": orients[int(rnd() * len(orients))],
                    "owner_kind": owner_kind,
                    "photo_url": f"https://picsum.photos/seed/{idx + 1000}/640/400",
                    "first_seen_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                    "last_seen_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                    "is_new": 0,
                }
                insert_property(conn, payload)

        return conn.execute("SELECT COUNT(*) AS c FROM properties").fetchone()["c"]


def list_properties(type_filter: Optional[str] = None, limit: int = 400) -> Dict[str, Any]:
    with get_connection() as conn:
        params: List[Any] = []
        count_params: List[Any] = []
        query = "SELECT * FROM properties"
        count_query = "SELECT COUNT(*) AS c FROM properties"
        if type_filter and type_filter != "todos":
            query += " WHERE type = ?"
            count_query += " WHERE type = ?"
            params.append(type_filter)
            count_params.append(type_filter)
        query += " ORDER BY first_seen_at DESC, id DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
        filtered_count = conn.execute(count_query, count_params).fetchone()["c"]
        total_count = conn.execute("SELECT COUNT(*) AS c FROM properties").fetchone()["c"]
        return {
            "properties": [serialize_property(row) for row in rows],
            "filteredCount": filtered_count,
            "totalCount": total_count,
        }


def get_landing_stats() -> Dict[str, Any]:
    with get_connection() as conn:
        total_properties = conn.execute("SELECT COUNT(*) AS c FROM properties").fetchone()["c"]
        new_today = conn.execute(
            "SELECT COUNT(*) AS c FROM properties WHERE is_new = 1 OR date(first_seen_at) = date('now')"
        ).fetchone()["c"]
        particulars = conn.execute(
            "SELECT COUNT(*) AS c FROM properties WHERE owner_kind = 'particular'"
        ).fetchone()["c"]
        zones_rows = conn.execute(
            "SELECT DISTINCT municipality FROM properties WHERE municipality IS NOT NULL AND municipality != '' ORDER BY municipality"
        ).fetchall()
        zones = [row["municipality"] for row in zones_rows]
        return {
            "totalProperties": total_properties,
            "newToday": new_today,
            "particulars": particulars,
            "zonesCount": len(zones),
            "zones": zones,
        }


class AppHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/health":
            self._send_json({"status": "ok"})
            return

        if path == "/api/properties":
            filter_value = parse_qs(parsed.query).get("type", ["todos"])[0]
            limit_value = parse_qs(parsed.query).get("limit", ["400"])[0]
            try:
                limit = int(limit_value)
            except ValueError:
                limit = 400
            data = list_properties(type_filter=filter_value, limit=limit)
            self._send_json(data)
            return

        if path == "/api/landing":
            self._send_json(get_landing_stats())
            return

        if path in {"/", "/home.html"}:
            content = INDEX_PATH.read_text(encoding="utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content.encode("utf-8"))))
            self.end_headers()
            self.wfile.write(content.encode("utf-8"))
            return

        if path == "/index.html":
            content = INDEX_PATH.read_text(encoding="utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content.encode("utf-8"))))
            self.end_headers()
            self.wfile.write(content.encode("utf-8"))
            return

        file_path = (ROOT / path.lstrip("/")).resolve()
        if file_path.exists() and file_path.is_file() and ROOT in file_path.parents:
            content = file_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", self._mime_type(file_path))
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        self.send_response(404)
        self.end_headers()
        self.wfile.write(b"Not Found")

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/vigilante/run":
            try:
                subprocess.run(
                    [sys.executable, str(ROOT / "vigilante.py")],
                    cwd=str(ROOT),
                    check=True,
                    capture_output=True,
                    text=True,
                )
                self._send_json({"status": "ok", "message": "Vigilante ejecutado correctamente."})
            except subprocess.CalledProcessError as exc:
                self._send_json({"status": "error", "message": exc.stderr or str(exc)})
            return

        self.send_response(404)
        self.end_headers()
        self.wfile.write(b"Not Found")

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return

    def _send_json(self, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _mime_type(self, path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix == ".css":
            return "text/css; charset=utf-8"
        if suffix == ".js":
            return "application/javascript; charset=utf-8"
        if suffix == ".json":
            return "application/json; charset=utf-8"
        if suffix in {".png", ".jpg", ".jpeg", ".webp"}:
            return f"image/{suffix[1:]}"
        return "application/octet-stream"


def main() -> None:
    init_db()
    seed_demo_data()
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), AppHandler)
    print(f"Server listening on http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
