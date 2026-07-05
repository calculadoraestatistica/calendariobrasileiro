#!/usr/bin/env python3
"""Scraper de proventos (dividendos/JCP) da B3 via statusinvest.com.br.

Fonte: endpoint publico GET /acao/getearnings (o mesmo que alimenta
https://statusinvest.com.br/acoes/proventos/ibovespa). Sem IndiceCode o
endpoint devolve todas as acoes da B3, nao apenas o Ibovespa.

Modos:
    python tools/scrape_dividends.py --backfill        # historico completo (2008+)
    python tools/scrape_dividends.py                   # incremental diario
    python tools/scrape_dividends.py --logos           # baixa logos que faltam

Saida (data/dividends/):
    meta.json        {updated_at, years, total_events, window}
    hist-YYYY.json   eventos com data-com naquele ano (historico fixo)
    recent.json      janela [mes atual -4, mes atual +13] + provisionados

Formato de evento (chaves curtas p/ reduzir payload):
    t   ticker            n    nome da empresa
    cid companyId         v    valor por acao (float)
    ty  tipo              dc   data com (YYYY-MM-DD)
    dp  data pagamento (YYYY-MM-DD ou null se indefinida)
    dy  dividend yield informado (float, pode ser 0)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "dividends"
LOGO_DIR = ROOT / "img" / "logos"

API = "https://statusinvest.com.br/acao/getearnings?IndiceCode=&Filter=&Start={start}&End={end}"
LOGO_URL = "https://statusinvest.com.br/img/company/avatar/{cid}.jpg"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)
HEADERS = {
    "User-Agent": UA,
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://statusinvest.com.br/acoes/proventos/ibovespa",
    "Accept": "application/json",
}

BACKFILL_START_YEAR = 2008
REQUEST_DELAY_S = 0.45
RETRIES = 3


def http_json(url: str) -> dict | None:
    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
            wait = 2 ** attempt
            print(f"  retry {attempt + 1}/{RETRIES} em {wait}s ({exc})", file=sys.stderr)
            time.sleep(wait)
    return None


def br_date_to_iso(s: str) -> str | None:
    """'01/07/2026' -> '2026-07-01'. '-' ou vazio -> None."""
    s = (s or "").strip()
    if not s or s == "-":
        return None
    try:
        d, m, y = s.split("/")
        return f"{y}-{m.zfill(2)}-{d.zfill(2)}"
    except ValueError:
        return None


def br_num(s: str) -> float:
    try:
        return float(str(s).replace(".", "").replace(",", "."))
    except (ValueError, AttributeError):
        return 0.0


def sane_date(iso: str | None) -> str | None:
    """Descarta datas malformadas da fonte (ex.: ano '204')."""
    if not iso:
        return None
    try:
        y = int(iso[:4])
    except ValueError:
        return None
    return iso if 1990 <= y <= date.today().year + 3 else None


def parse_item(raw: dict, provisioned: bool = False) -> dict | None:
    dc = sane_date(br_date_to_iso(raw.get("dateCom", "")))
    if not dc:
        return None
    ev = {
        "t": raw.get("code", "").upper(),
        "n": (raw.get("companyName") or "").strip().title(),
        "cid": raw.get("companyId"),
        "v": br_num(raw.get("resultAbsoluteValue", "0")),
        "ty": raw.get("earningType", ""),
        "dc": dc,
        "dp": sane_date(br_date_to_iso(raw.get("paymentDividend", ""))),
        "dy": br_num(raw.get("dy", "0")),
    }
    if provisioned:
        ev["prov"] = True
    return ev


def event_key(ev: dict) -> tuple:
    return (ev["t"], ev["dc"], ev.get("dp"), ev["ty"], round(ev["v"], 8))


def month_windows(y0: int, m0: int, y1: int, m1: int):
    """Gera (start_iso, end_iso) por mes de (y0,m0) ate (y1,m1) inclusive."""
    y, m = y0, m0
    while (y, m) <= (y1, m1):
        last = [31, 29 if y % 4 == 0 and (y % 100 != 0 or y % 400 == 0) else 28,
                31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1]
        yield f"{y}-{m:02d}-01", f"{y}-{m:02d}-{last}"
        m += 1
        if m > 12:
            m, y = 1, y + 1


def add_months(d: date, n: int) -> tuple[int, int]:
    total = d.year * 12 + (d.month - 1) + n
    return total // 12, total % 12 + 1


def fetch_window(start_iso: str, end_iso: str) -> tuple[list[dict], list[dict]]:
    """Retorna (eventos_datecom, provisionados) da janela."""
    data = http_json(API.format(start=start_iso, end=end_iso))
    if data is None:
        return [], []
    events = []
    for raw in data.get("dateCom", []) or []:
        ev = parse_item(raw)
        if ev:
            events.append(ev)
    # datePayment[] traz eventos cujo pagamento cai na janela; a data-com pode
    # estar fora do range varrido (ex.: anuncios antigos) — inclui p/ dedupe.
    for raw in data.get("datePayment", []) or []:
        ev = parse_item(raw)
        if ev:
            events.append(ev)
    prov = []
    for raw in data.get("provisioned", []) or []:
        ev = parse_item(raw, provisioned=True)
        if ev:
            prov.append(ev)
    return events, prov


def load_all_events() -> dict[tuple, dict]:
    """Carrega todos os eventos ja salvos (hist-*.json + recent.json)."""
    seen: dict[tuple, dict] = {}
    if not OUT_DIR.exists():
        return seen
    for f in sorted(OUT_DIR.glob("hist-*.json")):
        for ev in json.loads(f.read_text(encoding="utf-8")):
            seen[event_key(ev)] = ev
    recent = OUT_DIR / "recent.json"
    if recent.exists():
        payload = json.loads(recent.read_text(encoding="utf-8"))
        for ev in payload.get("events", []):
            seen[event_key(ev)] = ev
    return seen


def write_outputs(seen: dict[tuple, dict], provisioned: list[dict]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today()
    win_lo = "{0}-{1:02d}-01".format(*add_months(today, -4))
    y_hi, m_hi = add_months(today, 13)
    win_hi = f"{y_hi}-{m_hi:02d}-31"

    by_year: dict[int, list[dict]] = {}
    recent_events: list[dict] = []
    for ev in seen.values():
        year = int(ev["dc"][:4])
        by_year.setdefault(year, []).append(ev)
        in_window = (win_lo <= ev["dc"] <= win_hi) or (
            ev.get("dp") and win_lo <= ev["dp"] <= win_hi
        )
        if in_window:
            recent_events.append(ev)

    for year, evs in sorted(by_year.items()):
        evs.sort(key=lambda e: (e["dc"], e["t"]))
        (OUT_DIR / f"hist-{year}.json").write_text(
            json.dumps(evs, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )

    # dedupe provisionados contra eventos ja com pagamento definido
    prov_out = []
    prov_seen = set()
    for ev in provisioned:
        k = event_key(ev)
        if k in prov_seen:
            continue
        prov_seen.add(k)
        base = (ev["t"], ev["dc"], ev["ty"], round(ev["v"], 8))
        confirmed = any(
            (e["t"], e["dc"], e["ty"], round(e["v"], 8)) == base and e.get("dp")
            for e in seen.values()
        )
        if not confirmed:
            prov_out.append(ev)

    recent_events.sort(key=lambda e: (e["dc"], e["t"]))
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    (OUT_DIR / "recent.json").write_text(
        json.dumps(
            {
                "updated_at": now_iso,
                "window": [win_lo, win_hi],
                "events": recent_events,
                "provisioned": prov_out,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )
    (OUT_DIR / "meta.json").write_text(
        json.dumps(
            {
                "updated_at": now_iso,
                "source": "statusinvest.com.br (B3/CVM)",
                "years": sorted(by_year),
                "total_events": len(seen),
                "recent_events": len(recent_events),
                "provisioned": len(prov_out),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"OK: {len(seen)} eventos ({min(by_year)}-{max(by_year)}), "
          f"{len(recent_events)} na janela, {len(prov_out)} provisionados.")


def download_logos(seen: dict[tuple, dict]) -> None:
    LOGO_DIR.mkdir(parents=True, exist_ok=True)
    cids = sorted({ev["cid"] for ev in seen.values() if ev.get("cid")})
    missing = [c for c in cids if not (LOGO_DIR / f"{c}.jpg").exists()]
    print(f"Logos: {len(cids)} empresas, {len(missing)} faltando.")
    for i, cid in enumerate(missing, 1):
        try:
            req = urllib.request.Request(LOGO_URL.format(cid=cid), headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=20) as resp:
                blob = resp.read()
            if len(blob) > 500:
                (LOGO_DIR / f"{cid}.jpg").write_bytes(blob)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
            pass  # sem logo -> frontend cai no fallback de iniciais
        if i % 25 == 0:
            print(f"  {i}/{len(missing)}")
        time.sleep(0.25)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backfill", action="store_true", help="historico completo desde 2008")
    ap.add_argument("--logos", action="store_true", help="baixa logos faltantes e sai")
    args = ap.parse_args()

    seen = load_all_events()
    print(f"Eventos ja salvos: {len(seen)}")

    if args.logos:
        download_logos(seen)
        return 0

    today = date.today()
    if args.backfill:
        y1, m1 = add_months(today, 18)
        windows = list(month_windows(BACKFILL_START_YEAR, 1, y1, m1))
    else:
        y0, m0 = add_months(today, -4)
        y1, m1 = add_months(today, 14)
        windows = list(month_windows(y0, m0, y1, m1))

    print(f"Janelas a varrer: {len(windows)}")
    provisioned: list[dict] = []
    new_count = 0
    for i, (lo, hi) in enumerate(windows, 1):
        events, prov = fetch_window(lo, hi)
        provisioned.extend(prov)
        for ev in events:
            k = event_key(ev)
            if k not in seen:
                new_count += 1
            seen[k] = ev  # sempre sobrescreve (pagamento pode ter sido definido)
        if i % 12 == 0 or i == len(windows):
            print(f"  {i}/{len(windows)} janelas ({lo[:7]}) — {len(seen)} eventos, +{new_count} novos")
        time.sleep(REQUEST_DELAY_S)

    if not seen:
        print("ERRO: nenhum evento coletado — abortando sem escrever.", file=sys.stderr)
        return 1
    write_outputs(seen, provisioned)
    download_logos(seen)
    return 0


if __name__ == "__main__":
    sys.exit(main())
