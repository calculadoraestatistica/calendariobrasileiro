#!/usr/bin/env python3
"""Validate CalendarioBrasileiro.com.br static build."""

from __future__ import annotations

import html
import json
import sys
import xml.etree.ElementTree as ET
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
DOMAIN = "https://calendariobrasileiro.com.br"
START_YEAR = 2026
END_YEAR = 2030


class LinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self.h1_count = 0
        self.title = ""
        self.meta_description_count = 0
        self.canonical_count = 0
        self.lang = ""
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {name: value for name, value in attrs if value is not None}
        if tag == "html":
            self.lang = attr.get("lang", "")
        if tag == "h1":
            self.h1_count += 1
        if tag == "title":
            self._in_title = True
        if tag == "meta" and attr.get("name") == "description":
            self.meta_description_count += 1
        if tag == "link" and attr.get("rel") == "canonical":
            self.canonical_count += 1
        for key in ("href", "src"):
            if key in attr:
                self.links.append((key, attr[key] or ""))

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False


def local_target(raw_url: str, source: Path) -> Path | None:
    value = html.unescape(raw_url).strip()
    if not value or value.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
        return None
    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc:
        return None
    raw_path = unquote(parsed.path)
    if not raw_path:
        return None
    candidate = ROOT / raw_path.lstrip("/") if raw_path.startswith("/") else source.parent / raw_path
    if raw_path.endswith("/") or candidate.name == "":
        candidate = candidate / "index.html"
    return candidate.resolve()


def easter_sunday(year: int) -> date:
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def validate_json(errors: list[str]) -> None:
    for path in ROOT.rglob("*.json"):
        try:
            json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{path.relative_to(ROOT)}: JSON invalido: {exc}")


def validate_html(errors: list[str], warnings: list[str]) -> None:
    root_resolved = ROOT.resolve()
    for page in sorted(ROOT.glob("*.html")):
        parser = LinkCollector()
        parser.feed(page.read_text(encoding="utf-8"))
        if parser.lang != "pt-BR":
            errors.append(f"{page.name}: lang deveria ser pt-BR")
        if not parser.title.strip():
            errors.append(f"{page.name}: sem title")
        if parser.meta_description_count != 1:
            errors.append(f"{page.name}: meta description count {parser.meta_description_count}")
        if parser.canonical_count != 1:
            errors.append(f"{page.name}: canonical count {parser.canonical_count}")
        if parser.h1_count != 1:
            warnings.append(f"{page.name}: h1 count {parser.h1_count}")
        for attr, target in parser.links:
            resolved = local_target(target, page)
            if resolved is None:
                continue
            if not str(resolved).startswith(str(root_resolved)):
                errors.append(f"{page.name}: {attr} escapa da raiz -> {target}")
            elif not resolved.exists():
                errors.append(f"{page.name}: link local quebrado {attr} -> {target}")


def validate_sitemap(errors: list[str]) -> None:
    sitemap = ROOT / "sitemap.xml"
    if not sitemap.exists():
        errors.append("sitemap.xml ausente")
        return
    tree = ET.parse(sitemap)
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locs = [node.text or "" for node in tree.findall(".//sm:loc", ns)]
    expected = {
        DOMAIN + "/" if path.name == "index.html" else f"{DOMAIN}/{path.name}"
        for path in ROOT.glob("*.html")
        if path.name != "404.html"
    }
    # Articles live under /artigos/ and are part of the public site; accept them
    # in the sitemap (index.html maps to the bare /artigos/ URL).
    artigos_dir = ROOT / "artigos"
    if artigos_dir.is_dir():
        for path in artigos_dir.glob("*.html"):
            if path.name == "index.html":
                expected.add(f"{DOMAIN}/artigos/")
            else:
                expected.add(f"{DOMAIN}/artigos/{path.name}")
    for url in sorted(expected - set(locs)):
        errors.append(f"sitemap sem URL: {url}")
    for url in sorted(set(locs) - expected):
        errors.append(f"sitemap URL inesperada: {url}")


def validate_assets(errors: list[str]) -> None:
    required = [
        "CNAME",
        "ads.txt",
        "robots.txt",
        "site.webmanifest",
        "favicon.svg",
        "css/style.css",
        "js/calendar-tools.js",
        "js/calendar-data.js",
        "data/calendarios.json",
    ]
    for name in required:
        if not (ROOT / name).exists():
            errors.append(f"asset ausente: {name}")
    cname = (ROOT / "CNAME").read_text(encoding="utf-8").strip() if (ROOT / "CNAME").exists() else ""
    if cname != "calendariobrasileiro.com.br":
        errors.append(f"CNAME incorreto: {cname}")


def validate_calendar_data(errors: list[str]) -> None:
    data_path = ROOT / "data" / "calendarios.json"
    if not data_path.exists():
        errors.append("data/calendarios.json ausente")
        return
    data = json.loads(data_path.read_text(encoding="utf-8"))
    years = data.get("years", {})
    known = {
        2026: {"Páscoa": "2026-04-05", "Carnaval (segunda)": "2026-02-16", "Corpus Christi": "2026-06-04"},
        2027: {"Páscoa": "2027-03-28", "Carnaval (segunda)": "2027-02-08", "Corpus Christi": "2027-05-27"},
        2028: {"Páscoa": "2028-04-16", "Carnaval (segunda)": "2028-02-28", "Corpus Christi": "2028-06-15"},
    }
    for year in range(START_YEAR, END_YEAR + 1):
        if str(year) not in years:
            errors.append(f"ano ausente no JSON: {year}")
            continue
        holidays = years[str(year)].get("holidays", [])
        by_name = {}
        for item in holidays:
            by_name.setdefault(item["name"], item["date"])
        if by_name.get("Natal") != f"{year}-12-25":
            errors.append(f"{year}: Natal incorreto")
        if by_name.get("Dia Nacional de Zumbi e da Consciência Negra") != f"{year}-11-20":
            errors.append(f"{year}: Consciência Negra incorreta")
        if date.fromisoformat(by_name.get("Páscoa")) != easter_sunday(year):
            errors.append(f"{year}: Páscoa não bate com algoritmo")
        for name, expected in known.get(year, {}).items():
            if by_name.get(name) != expected:
                errors.append(f"{year}: {name} = {by_name.get(name)}, esperado {expected}")


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    validate_assets(errors)
    validate_json(errors)
    validate_html(errors, warnings)
    validate_sitemap(errors)
    validate_calendar_data(errors)
    print(f"HTML files: {len(list(ROOT.glob('*.html')))}")
    print(f"Warnings: {len(warnings)}")
    for warning in warnings[:50]:
        print("WARN:", warning)
    print(f"Errors: {len(errors)}")
    for error in errors[:200]:
        print("ERROR:", error)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
