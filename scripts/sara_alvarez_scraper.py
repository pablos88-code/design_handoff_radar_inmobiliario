#!/usr/bin/env python3
import html
import re
import urllib.request
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

BASE_URL = "https://www.saraalvarezinmobiliaria.com"
SECTION_PATHS = [
    "/comprar/pisos",
    "/comprar/casas",
    "/comprar/locales",
    "/comprar/solares",
    "/comprar/garajes",
    "/alquilar/pisos",
    "/alquilar/casas",
    "/alquilar/locales",
    "/alquilar/garajes",
    "/alquilar/solares",
]
SECTION_TYPE = {
    "/comprar/pisos": "venta",
    "/comprar/casas": "venta",
    "/comprar/locales": "venta",
    "/comprar/solares": "venta",
    "/comprar/garajes": "venta",
    "/alquilar/pisos": "alquiler",
    "/alquilar/casas": "alquiler",
    "/alquilar/locales": "alquiler",
    "/alquilar/garajes": "alquiler",
    "/alquilar/solares": "alquiler",
}
PROPERTY_TYPE_BY_SECTION = {
    "/comprar/pisos": "Piso",
    "/comprar/casas": "Casa",
    "/comprar/locales": "Local",
    "/comprar/solares": "Solar",
    "/comprar/garajes": "Garaje",
    "/alquilar/pisos": "Piso",
    "/alquilar/casas": "Casa",
    "/alquilar/locales": "Local",
    "/alquilar/garajes": "Garaje",
    "/alquilar/solares": "Solar",
}

ZONE_COORDINATES = {
    "pontevedra": (42.4318, -8.6446),
    "sanxenxo": (42.4790, -8.8570),
    "marin": (42.3910, -8.7020),
    "moraña": (42.6630, -8.5770),
    "vigo": (42.2406, -8.7207),
    "bueu": (42.3251, -8.7860),
    "poio": (42.4669, -8.7270),
    "bora": (42.4370, -8.5850),
    "cela": (42.3180, -8.7620),
    "beluso": (42.3300, -8.8150),
    "a caeria": (42.4345, -8.6585),
    "marcon": (42.4180, -8.6050),
    "moura": (42.4260, -8.5980),
    "ponte caldelas": (42.3994, -8.4528),
}


def get_html(url: str, timeout: int = 30) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def normalize_text(value: Optional[str]) -> str:
    if not value:
        return ""
    text = html.unescape(value)
    return " ".join(text.replace("\xa0", " ").strip().split())


def parse_price(value: Optional[str]) -> Optional[float]:
    if not value:
        return None
    text = normalize_text(value)
    if not text or "consult" in text.lower():
        return None
    digits = re.findall(r"[0-9]+(?:\.[0-9]{3})*", text)
    if not digits:
        return None
    numeric = digits[0].replace('.', '')
    try:
        return float(numeric)
    except ValueError:
        return None


def parse_int(value: Optional[str]) -> Optional[int]:
    if not value:
        return None
    digits = re.search(r"(\d+)", normalize_text(value))
    return int(digits.group(1)) if digits else None


def absolute_url(path: str) -> str:
    if not path:
        return ""
    if path.startswith("//"):
        return "https:" + path
    if path.startswith("http"):
        return path
    return urljoin(BASE_URL, path)


def resolve_municipality(url: str, subtitle: str) -> str:
    if subtitle:
        parts = [part.strip() for part in subtitle.split(">") if part.strip()]
        if parts:
            return parts[0]
    parsed = urlparse(url)
    segments = [p for p in parsed.path.split("/") if p]
    if len(segments) >= 4:
        return segments[2]
    if len(segments) >= 3:
        return segments[-2]
    return "Pontevedra"


def resolve_coordinates(municipality: str) -> Dict[str, float]:
    if not municipality:
        municipality = "Pontevedra"
    key = municipality.strip().lower()
    for name, coords in ZONE_COORDINATES.items():
        if name in key:
            return {"lat": coords[0], "lng": coords[1]}
    for name, coords in ZONE_COORDINATES.items():
        if key in name:
            return {"lat": coords[0], "lng": coords[1]}
    return {"lat": 42.4318, "lng": -8.6446}


def extract_listing_blocks(html_text: str) -> List[str]:
    start = html_text.find('<div id="minifichas"')
    if start == -1:
        start = 0
    end = html_text.find('<div id="pie_pagina_ancho"', start)
    fragment = html_text[start:end] if end != -1 else html_text[start:]
    return re.findall(r'(<a[^>]+class="ev-property-container[^"]*"[^>]*>.*?</a>)', fragment, re.S)


def parse_listing_block(block: str, section_path: str) -> Optional[Dict[str, any]]:
    href_match = re.search(r'href=["\']([^"\']+)["\']', block)
    if not href_match:
        return None
    url = absolute_url(href_match.group(1))
    title_match = re.search(r'<div class="ev-teaser-title">(.*?)</div>', block, re.S)
    title = normalize_text(title_match.group(1)) if title_match else "Sin título"
    subtitle_match = re.search(r'class="ev-teaser-subtitle"\s*>\s*([^<]+)', block, re.S)
    subtitle = normalize_text(subtitle_match.group(1)) if subtitle_match else ""
    address = subtitle.replace(' > ', ', ') if subtitle else title
    municipality = resolve_municipality(url, subtitle)
    image_match = re.search(r'<img[^>]+(?:data-src|src)=["\']([^"\']+)["\']', block)
    photo_url = absolute_url(image_match.group(1)) if image_match else ""
    price_match = re.search(r'class="ev-value">\s*([^<]+)<', block, re.S)
    price = parse_price(price_match.group(1) if price_match else None)
    bedrooms = None
    bathrooms = None
    m2 = None
    for attribute in re.findall(r'<div class="ev-teaser-attribute">(.*?)</div>', block, re.S):
        label_match = re.search(r'alt=["\']([^"\']+)["\']', attribute)
        value_match = re.search(r'<span class="ev-teaser-attribute-value">([^<]+)</span>', attribute, re.S)
        if not label_match or not value_match:
            continue
        label = normalize_text(label_match.group(1)).lower()
        value = normalize_text(value_match.group(1))
        if 'dormitorios' in label or 'habitación' in label:
            bedrooms = parse_int(value)
        elif 'baños' in label:
            bathrooms = parse_int(value)
        elif 'm²' in value.lower() or 'superficie' in label:
            m2 = parse_int(value)
    property_type = PROPERTY_TYPE_BY_SECTION.get(section_path, "Propiedad")
    type_value = SECTION_TYPE.get(section_path, "venta")
    return {
        "source": "Sara Álvarez Inmobiliaria",
        "source_url": url,
        "type": type_value,
        "price": price,
        "currency": "EUR",
        "lat": resolve_coordinates(municipality)["lat"],
        "lng": resolve_coordinates(municipality)["lng"],
        "location_precision": "approx",
        "title": title,
        "address": address,
        "municipality": municipality,
        "ptype": property_type,
        "rooms": bedrooms,
        "baths": bathrooms,
        "m2": m2,
        "orientation": None,
        "owner_kind": "agencia",
        "photo_url": photo_url,
    }


def find_next_page(html_text: str, current_url: str) -> Optional[str]:
    next_match = re.search(r'<a[^>]+href=["\']([^"\']*paginaActual=\d+)["\'][^>]*>\s*Siguiente\s*</a>', html_text, re.I)
    if next_match:
        return absolute_url(next_match.group(1))
    return None


def scrape_section(section_path: str) -> List[Dict[str, any]]:
    items: List[Dict[str, any]] = []
    next_url = absolute_url(section_path)
    visited = set()
    while next_url and next_url not in visited:
        visited.add(next_url)
        html_text = get_html(next_url)
        blocks = extract_listing_blocks(html_text)
        for block in blocks:
            listing = parse_listing_block(block, section_path)
            if listing:
                items.append(listing)
        next_page = find_next_page(html_text, next_url)
        next_url = next_page if next_page and next_page not in visited else None
    return items


def fetch_sara_alvarez_ads() -> List[Dict[str, any]]:
    results: Dict[str, Dict[str, any]] = {}
    for section_path in SECTION_PATHS:
        section_items = scrape_section(section_path)
        for item in section_items:
            if not item.get("source_url"):
                continue
            results[item["source_url"]] = item
    return list(results.values())


if __name__ == "__main__":
    ads = fetch_sara_alvarez_ads()
    print(f"Found {len(ads)} Sara Álvarez Inmobiliaria ads")
    for ad in ads[:5]:
        print(ad["source_url"], ad["title"], ad["price"], ad["municipality"], ad["ptype"])
