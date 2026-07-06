#!/usr/bin/env python3
"""Generate CalendarioBrasileiro.com.br as a static site.

Architecture mirrors DanskeDage.dk: zero-dependency single-file generator with a
shared ``layout`` rendering function, hero + quick-panel, ad slots, breadcrumb
nav + JSON-LD, FAQ + FAQPage JSON-LD, sitemap, calendar JSON artifacts and a
pure-Python PNG writer for favicons + OG image.

Coverage 2026-2050:
    - calendario-ANO + calendario-MES-ANO (12)
    - feriados-ANO + feriados-bancarios-ANO
    - feriados-CAPITAL-UF-ANO and feriados-estado-UF-ANO
    - dias-uteis-ANO and dias-uteis-UF-ANO
    - carnaval-ANO, pascoa-ANO, corpus-christi-ANO
    - melhores-dias-para-folga-ANO and prazos-ANO
    - tools (index, calcular, adicionar, numero-da-semana, calendario-bancario,
      feriados-estaduais) + institutional/trust pages.
"""

from __future__ import annotations

import argparse
import calendar
import html
import json
import struct
import sys
import unicodedata
import zlib
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

# Make the local "tools" folder importable so we can pull in the extra-tool
# renderers without requiring the user to set PYTHONPATH.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from extra_tool_pages import render_all as render_extra_tools  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DOMAIN = "https://calendariobrasileiro.com.br"
SITE_NAME = "Calendario Brasileiro"
SITE_NAME_DISPLAY = "Calendário Brasileiro"
ADS_CLIENT = "ca-pub-7516029395999799"
CONTACT_EMAIL = "calculadoraestatistica@gmail.com"
BUY_ME_A_COFFEE = "https://buymeacoffee.com/calculadoraestatistica"
START_YEAR_DEFAULT = 2026
END_YEAR_DEFAULT = 2030  # ano corrente + 4 próximos
ACTIVE_YEAR = date.today().year

MONTHS = [
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
]
MONTH_SLUGS = [
    "janeiro",
    "fevereiro",
    "marco",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
]
WEEKDAYS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
WEEKDAYS_LONG = [
    "segunda-feira",
    "terça-feira",
    "quarta-feira",
    "quinta-feira",
    "sexta-feira",
    "sábado",
    "domingo",
]


@dataclass(frozen=True)
class Holiday:
    date: date
    name: str
    kind: str
    scope: str
    official: bool
    note: str = ""


STATES = [
    {"uf": "AC", "name": "Acre", "slug": "acre", "capital": "Rio Branco", "capital_slug": "rio-branco"},
    {"uf": "AL", "name": "Alagoas", "slug": "alagoas", "capital": "Maceió", "capital_slug": "maceio"},
    {"uf": "AP", "name": "Amapá", "slug": "amapa", "capital": "Macapá", "capital_slug": "macapa"},
    {"uf": "AM", "name": "Amazonas", "slug": "amazonas", "capital": "Manaus", "capital_slug": "manaus"},
    {"uf": "BA", "name": "Bahia", "slug": "bahia", "capital": "Salvador", "capital_slug": "salvador"},
    {"uf": "CE", "name": "Ceará", "slug": "ceara", "capital": "Fortaleza", "capital_slug": "fortaleza"},
    {"uf": "DF", "name": "Distrito Federal", "slug": "distrito-federal", "capital": "Brasília", "capital_slug": "brasilia"},
    {"uf": "ES", "name": "Espírito Santo", "slug": "espirito-santo", "capital": "Vitória", "capital_slug": "vitoria"},
    {"uf": "GO", "name": "Goiás", "slug": "goias", "capital": "Goiânia", "capital_slug": "goiania"},
    {"uf": "MA", "name": "Maranhão", "slug": "maranhao", "capital": "São Luís", "capital_slug": "sao-luis"},
    {"uf": "MT", "name": "Mato Grosso", "slug": "mato-grosso", "capital": "Cuiabá", "capital_slug": "cuiaba"},
    {"uf": "MS", "name": "Mato Grosso do Sul", "slug": "mato-grosso-do-sul", "capital": "Campo Grande", "capital_slug": "campo-grande"},
    {"uf": "MG", "name": "Minas Gerais", "slug": "minas-gerais", "capital": "Belo Horizonte", "capital_slug": "belo-horizonte"},
    {"uf": "PA", "name": "Pará", "slug": "para", "capital": "Belém", "capital_slug": "belem"},
    {"uf": "PB", "name": "Paraíba", "slug": "paraiba", "capital": "João Pessoa", "capital_slug": "joao-pessoa"},
    {"uf": "PR", "name": "Paraná", "slug": "parana", "capital": "Curitiba", "capital_slug": "curitiba"},
    {"uf": "PE", "name": "Pernambuco", "slug": "pernambuco", "capital": "Recife", "capital_slug": "recife"},
    {"uf": "PI", "name": "Piauí", "slug": "piaui", "capital": "Teresina", "capital_slug": "teresina"},
    {"uf": "RJ", "name": "Rio de Janeiro", "slug": "rio-de-janeiro", "capital": "Rio de Janeiro", "capital_slug": "rio-de-janeiro"},
    {"uf": "RN", "name": "Rio Grande do Norte", "slug": "rio-grande-do-norte", "capital": "Natal", "capital_slug": "natal"},
    {"uf": "RS", "name": "Rio Grande do Sul", "slug": "rio-grande-do-sul", "capital": "Porto Alegre", "capital_slug": "porto-alegre"},
    {"uf": "RO", "name": "Rondônia", "slug": "rondonia", "capital": "Porto Velho", "capital_slug": "porto-velho"},
    {"uf": "RR", "name": "Roraima", "slug": "roraima", "capital": "Boa Vista", "capital_slug": "boa-vista"},
    {"uf": "SC", "name": "Santa Catarina", "slug": "santa-catarina", "capital": "Florianópolis", "capital_slug": "florianopolis"},
    {"uf": "SP", "name": "São Paulo", "slug": "sao-paulo", "capital": "São Paulo", "capital_slug": "sao-paulo"},
    {"uf": "SE", "name": "Sergipe", "slug": "sergipe", "capital": "Aracaju", "capital_slug": "aracaju"},
    {"uf": "TO", "name": "Tocantins", "slug": "tocantins", "capital": "Palmas", "capital_slug": "palmas"},
]


STATE_HOLIDAYS = {
    "AC": [(6, 15, "Aniversário do Acre"), (11, 17, "Tratado de Petrópolis")],
    "AL": [(9, 16, "Emancipação política de Alagoas")],
    "AP": [(3, 19, "Dia de São José"), (9, 13, "Criação do Território Federal do Amapá")],
    "AM": [(9, 5, "Elevação do Amazonas à categoria de província")],
    "BA": [(7, 2, "Independência da Bahia")],
    "CE": [(3, 25, "Data Magna do Ceará")],
    "DF": [(4, 21, "Aniversário de Brasília")],
    "ES": [],
    "GO": [(10, 24, "Aniversário de Goiânia")],
    "MA": [(7, 28, "Adesão do Maranhão à Independência")],
    "MT": [],
    "MS": [(10, 11, "Criação de Mato Grosso do Sul")],
    "MG": [(4, 21, "Data Magna de Minas Gerais")],
    "PA": [(8, 15, "Adesão do Pará à Independência")],
    "PB": [(8, 5, "Fundação da Paraíba")],
    "PR": [(12, 19, "Emancipação política do Paraná")],
    "PE": [(3, 6, "Data Magna de Pernambuco"), (6, 24, "São João")],
    "PI": [(10, 19, "Dia do Piauí")],
    "RJ": [(4, 23, "São Jorge")],
    "RN": [(10, 3, "Mártires de Cunhaú e Uruaçu")],
    "RS": [(9, 20, "Revolução Farroupilha")],
    "RO": [(1, 4, "Criação de Rondônia")],
    "RR": [(10, 5, "Criação de Roraima")],
    "SC": [(8, 11, "Criação da Capitania de Santa Catarina")],
    "SP": [(7, 9, "Revolução Constitucionalista")],
    "SE": [(7, 8, "Emancipação política de Sergipe")],
    "TO": [(10, 5, "Criação do Tocantins")],
}

CITY_HOLIDAYS = {
    "rio-branco-ac": [(6, 15, "Aniversário do Acre"), (12, 28, "Aniversário de Rio Branco")],
    "maceio-al": [(8, 27, "Nossa Senhora dos Prazeres"), (9, 16, "Emancipação de Alagoas")],
    "macapa-ap": [(2, 4, "Aniversário de Macapá"), (3, 19, "São José")],
    "manaus-am": [(9, 5, "Elevação do Amazonas"), (10, 24, "Aniversário de Manaus")],
    "salvador-ba": [(7, 2, "Independência da Bahia"), (12, 8, "Nossa Senhora da Conceição")],
    "fortaleza-ce": [(3, 25, "Data Magna do Ceará"), (8, 15, "Nossa Senhora da Assunção")],
    "brasilia-df": [(4, 21, "Aniversário de Brasília")],
    "vitoria-es": [(9, 8, "Nossa Senhora da Vitória")],
    "goiania-go": [(5, 24, "Nossa Senhora Auxiliadora"), (10, 24, "Aniversário de Goiânia")],
    "sao-luis-ma": [(7, 28, "Adesão do Maranhão à Independência"), (9, 8, "Aniversário de São Luís")],
    "cuiaba-mt": [(4, 8, "Aniversário de Cuiabá")],
    "campo-grande-ms": [(8, 26, "Aniversário de Campo Grande"), (10, 11, "Criação de Mato Grosso do Sul")],
    "belo-horizonte-mg": [(8, 15, "Nossa Senhora da Boa Viagem"), (12, 8, "Imaculada Conceição")],
    "belem-pa": [(1, 12, "Aniversário de Belém"), (8, 15, "Adesão do Pará à Independência")],
    "joao-pessoa-pb": [(8, 5, "Aniversário de João Pessoa e Fundação da Paraíba")],
    "curitiba-pr": [(9, 8, "Nossa Senhora da Luz dos Pinhais"), (12, 19, "Emancipação do Paraná")],
    "recife-pe": [(3, 6, "Data Magna de Pernambuco"), (6, 24, "São João"), (7, 16, "Nossa Senhora do Carmo")],
    "teresina-pi": [(8, 16, "Aniversário de Teresina"), (10, 19, "Dia do Piauí")],
    "rio-de-janeiro-rj": [(1, 20, "São Sebastião"), (4, 23, "São Jorge")],
    "natal-rn": [(10, 3, "Mártires de Cunhaú e Uruaçu"), (11, 21, "Nossa Senhora da Apresentação")],
    "porto-alegre-rs": [(2, 2, "Nossa Senhora dos Navegantes"), (9, 20, "Revolução Farroupilha")],
    "porto-velho-ro": [(1, 4, "Criação de Rondônia"), (1, 24, "Instalação do município de Porto Velho")],
    "boa-vista-rr": [(7, 9, "Aniversário de Boa Vista"), (10, 5, "Criação de Roraima")],
    "florianopolis-sc": [(3, 23, "Aniversário de Florianópolis"), (8, 11, "Criação da Capitania de Santa Catarina")],
    "sao-paulo-sp": [(1, 25, "Aniversário de São Paulo"), (7, 9, "Revolução Constitucionalista")],
    "aracaju-se": [(3, 17, "Aniversário de Aracaju"), (7, 8, "Emancipação de Sergipe")],
    "palmas-to": [(5, 20, "Aniversário de Palmas"), (10, 5, "Criação do Tocantins")],
}


# ----------------------------------------------------------------------------- helpers


def slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
    out = []
    last_dash = False
    for ch in ascii_text:
        if ch.isalnum():
            out.append(ch)
            last_dash = False
        elif not last_dash:
            out.append("-")
            last_dash = True
    return "".join(out).strip("-")


def fmt_date(d: date) -> str:
    return f"{d.day} de {MONTHS[d.month - 1]} de {d.year}"


def fmt_short(d: date) -> str:
    return d.strftime("%d/%m/%Y")


def iso(d: date) -> str:
    return d.isoformat()


def daterange(start: date, end: date) -> Iterable[date]:
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def easter_sunday(year: int) -> date:
    """Gregorian Easter Sunday (Meeus/Jones/Butcher)."""
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


# ----------------------------------------------------------------------------- holidays


def national_holidays(year: int) -> list[Holiday]:
    e = easter_sunday(year)
    fixed = [
        (1, 1, "Confraternização Universal", "feriado nacional", True, "Lei nº 662/1949, com alterações posteriores."),
        (4, 21, "Tiradentes", "feriado nacional", True, "Lei nº 10.607/2002."),
        (5, 1, "Dia do Trabalho", "feriado nacional", True, "Lei nº 10.607/2002."),
        (9, 7, "Independência do Brasil", "feriado nacional", True, "Lei nº 10.607/2002."),
        (10, 12, "Nossa Senhora Aparecida", "feriado nacional", True, "Lei nº 6.802/1980."),
        (11, 2, "Finados", "feriado nacional", True, "Lei nº 10.607/2002."),
        (11, 15, "Proclamação da República", "feriado nacional", True, "Lei nº 10.607/2002."),
        (11, 20, "Dia Nacional de Zumbi e da Consciência Negra", "feriado nacional", True, "Lei nº 14.759/2023."),
        (12, 25, "Natal", "feriado nacional", True, "Lei nº 10.607/2002."),
    ]
    items = [Holiday(date(year, m, d), name, kind, "Brasil", off, note) for m, d, name, kind, off, note in fixed]
    items.extend([
        Holiday(e - timedelta(days=48), "Carnaval (segunda)", "ponto facultativo / feriado bancário", "Brasil", False, "Não é feriado nacional civil; aparece no calendário bancário."),
        Holiday(e - timedelta(days=47), "Carnaval (terça)", "ponto facultativo / feriado bancário", "Brasil", False, "Não é feriado nacional civil; aparece no calendário bancário."),
        Holiday(e - timedelta(days=46), "Quarta-feira de Cinzas", "expediente especial", "Brasil", False, "Bancos com expediente parcial; muitas cidades com ponto facultativo."),
        Holiday(e - timedelta(days=2), "Sexta-feira Santa", "feriado religioso comum", "Brasil", False, "Feriado religioso adotado por estados e municípios."),
        Holiday(e, "Páscoa", "data comemorativa", "Brasil", False, "Domingo de Páscoa."),
        Holiday(e + timedelta(days=60), "Corpus Christi", "ponto facultativo / feriado bancário", "Brasil", False, "Não é feriado nacional civil; é feriado municipal/bancário."),
    ])
    return sorted(items, key=lambda h: h.date)


def standard_nonwork_dates(year: int) -> set[date]:
    names = {
        "Confraternização Universal",
        "Tiradentes",
        "Dia do Trabalho",
        "Independência do Brasil",
        "Nossa Senhora Aparecida",
        "Finados",
        "Proclamação da República",
        "Dia Nacional de Zumbi e da Consciência Negra",
        "Natal",
        "Sexta-feira Santa",
        "Corpus Christi",
    }
    return {h.date for h in national_holidays(year) if h.name in names}


def legal_national_dates(year: int) -> set[date]:
    return {h.date for h in national_holidays(year) if h.official}


def banking_holidays(year: int) -> list[Holiday]:
    e = easter_sunday(year)
    keep = {
        "Confraternização Universal",
        "Tiradentes",
        "Dia do Trabalho",
        "Independência do Brasil",
        "Nossa Senhora Aparecida",
        "Finados",
        "Proclamação da República",
        "Dia Nacional de Zumbi e da Consciência Negra",
        "Natal",
        "Carnaval (segunda)",
        "Carnaval (terça)",
        "Sexta-feira Santa",
        "Corpus Christi",
    }
    items = [
        Holiday(h.date, h.name, "feriado bancário", "Brasil", h.name not in {"Carnaval (segunda)", "Carnaval (terça)", "Sexta-feira Santa", "Corpus Christi"}, h.note)
        for h in national_holidays(year) if h.name in keep
    ]
    items.append(Holiday(e - timedelta(days=46), "Quarta-feira de Cinzas", "expediente bancário especial", "Brasil", False, "Bancos abrem após 12h conforme orientação FEBRABAN."))
    last = date(year, 12, 31)
    bank_dates = {i.date for i in items if i.kind == "feriado bancário"}
    while last.weekday() >= 5 or last in bank_dates:
        last -= timedelta(days=1)
    items.append(Holiday(last, "Último dia útil bancário", "sem expediente bancário ao público", "Brasil", False, "Sem atendimento ao público, conforme calendário bancário."))
    return sorted(items, key=lambda h: h.date)


def state_by_uf(uf: str) -> dict:
    return next(s for s in STATES if s["uf"] == uf)


def state_holidays(year: int, uf: str) -> list[Holiday]:
    s = state_by_uf(uf)
    return [
        Holiday(date(year, m, d), name, "feriado estadual / data magna", s["name"], True, "Data local cadastrada; confirme a legislação estadual para usos formais.")
        for m, d, name in STATE_HOLIDAYS.get(uf, [])
    ]


def city_holidays(year: int, city_key: str) -> list[Holiday]:
    s = next(item for item in STATES if f"{item['capital_slug']}-{item['uf'].lower()}" == city_key)
    return [
        Holiday(date(year, m, d), name, "feriado municipal / data local", f"{s['capital']} - {s['uf']}", True, "Confirme com a prefeitura para usos formais.")
        for m, d, name in CITY_HOLIDAYS.get(city_key, [])
    ]


def merge_holidays(items: Iterable[Holiday]) -> list[Holiday]:
    by_date: dict[date, Holiday] = {}
    for item in sorted(items, key=lambda h: (h.date, h.name)):
        if item.date not in by_date:
            by_date[item.date] = item
        else:
            existing = by_date[item.date]
            names = existing.name.split(" / ")
            if item.name not in names:
                names.append(item.name)
            by_date[item.date] = Holiday(
                item.date,
                " / ".join(names),
                existing.kind if existing.kind == item.kind else f"{existing.kind}; {item.kind}",
                existing.scope if existing.scope == item.scope else f"{existing.scope}; {item.scope}",
                existing.official or item.official,
                existing.note or item.note,
            )
    return list(by_date.values())


def holidays_for_scope(year: int, uf: str | None = None, city_key: str | None = None) -> list[Holiday]:
    items = list(national_holidays(year))
    if uf:
        items.extend(state_holidays(year, uf))
    if city_key:
        items.extend(city_holidays(year, city_key))
    return merge_holidays(items)


def nonwork_dates_for_scope(year: int, uf: str | None = None, city_key: str | None = None) -> set[date]:
    dates = set(standard_nonwork_dates(year))
    if uf:
        dates.update(h.date for h in state_holidays(year, uf))
    if city_key:
        dates.update(h.date for h in city_holidays(year, city_key))
    return dates


def is_workday(d: date, uf: str | None = None, city_key: str | None = None) -> bool:
    return d.weekday() < 5 and d not in nonwork_dates_for_scope(d.year, uf, city_key)


def is_bank_business_day(d: date) -> bool:
    excluded = {h.date for h in banking_holidays(d.year) if h.kind == "feriado bancário" or h.kind == "sem expediente bancário ao público"}
    return d.weekday() < 5 and d not in excluded


def year_stats(year: int, uf: str | None = None, city_key: str | None = None) -> dict:
    days = list(daterange(date(year, 1, 1), date(year, 12, 31)))
    nonwork = nonwork_dates_for_scope(year, uf, city_key)
    return {
        "days": len(days),
        "weekend_days": sum(1 for d in days if d.weekday() >= 5),
        "holidays": len(nonwork),
        "holidays_on_weekdays": sum(1 for d in nonwork if d.weekday() < 5),
        "workdays": sum(1 for d in days if d.weekday() < 5 and d not in nonwork),
        "bank_business_days": sum(1 for d in days if is_bank_business_day(d)),
        "iso_weeks": date(year, 12, 28).isocalendar().week,
    }


def build_best_vacation_windows(year: int) -> list[dict]:
    first = date(year, 1, 1)
    last = date(year, 12, 31)
    nonwork = standard_nonwork_dates(year)
    candidates = []
    for offset in range((last - first).days + 1):
        start = first + timedelta(days=offset)
        for length in range(4, 17):
            end = start + timedelta(days=length - 1)
            if end.year != year:
                continue
            days = list(daterange(start, end))
            vacation_days = [d for d in days if is_workday(d)]
            if not vacation_days or len(vacation_days) > 6:
                continue
            ratio = len(days) / len(vacation_days)
            names = [h.name for h in national_holidays(year) if h.date in days and h.date in nonwork]
            if ratio >= 2 or names:
                candidates.append({
                    "start": start,
                    "end": end,
                    "days_off": len(days),
                    "vacation_days": len(vacation_days),
                    "ratio": ratio,
                    "holidays": ", ".join(names) if names else "fins de semana",
                })
    candidates.sort(key=lambda x: (x["ratio"], x["days_off"]), reverse=True)
    picked: list[dict] = []
    used: list[tuple[date, date]] = []
    for item in candidates:
        if any(not (item["end"] < a or item["start"] > b) for a, b in used):
            continue
        picked.append(item)
        used.append((item["start"], item["end"]))
        if len(picked) == 10:
            break
    return sorted(picked, key=lambda x: x["start"])


# ----------------------------------------------------------------------------- assets


def css_text() -> str:
    return """\
:root{--bg:#faf7f0;--paper:#fffdf7;--ink:#1c1917;--muted:#57534e;--line:#d6cec2;--brand:#14532d;--brand2:#0f766e;--accent:#b45309;--soft:#eef3ea;--danger:#b91c1c;--hol:#b91c1c;--hol-bg:#f9e9e7;--sp-ink:#8a4b09;--sp-bg:#f7efdc;--wk-ink:#5b6472;--wk-bg:#eef0f3;--serif:Georgia,'Times New Roman',serif;--sans:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;--radius:2px;--shadow:2px 2px 0 rgba(28,25,23,.9)}
*{box-sizing:border-box}html{font-family:var(--sans);color:var(--ink);background:var(--bg);line-height:1.55}body{margin:0}h1,h2,h3,h4{font-family:var(--serif);letter-spacing:-.005em}a{color:#14532d}a:hover{color:#0c3d20}.skip-link{position:absolute;left:-999px}.skip-link:focus{left:1rem;top:1rem;background:var(--paper);padding:.6rem 1rem;border:2px solid var(--brand);z-index:99}.container{width:min(1140px,calc(100% - 32px));margin-inline:auto}.container--narrow{width:min(820px,calc(100% - 32px));margin-inline:auto}
.site-header{background:var(--paper);border-top:4px solid var(--brand);border-bottom:1px solid var(--line);position:sticky;top:0;z-index:20}.site-header__inner{display:flex;align-items:center;gap:1rem;justify-content:space-between;min-height:64px}.brand{display:flex;align-items:center;gap:.6rem;text-decoration:none;color:var(--ink)}.brand span{font-family:var(--serif);font-weight:700;font-size:1.18rem;letter-spacing:.01em}.brand__mark{width:34px;height:34px}.brand--footer{color:#fff}
.main-nav ul{list-style:none;margin:0;padding:0;display:flex;gap:.15rem;flex-wrap:wrap}.main-nav a{display:block;text-decoration:none;color:var(--muted);padding:.62rem .55rem .5rem;border-radius:0;border-bottom:2px solid transparent;font-weight:700;font-size:.78rem;text-transform:uppercase;letter-spacing:.07em}.main-nav a[aria-current=page],.main-nav a:hover{background:transparent;color:var(--ink);border-bottom-color:var(--brand)}
.hero{padding:2.6rem 0 1.9rem;background:var(--bg);border-bottom:1px solid var(--line)}.hero-grid{display:grid;grid-template-columns:minmax(0,1.05fr) minmax(280px,.95fr);gap:2rem;align-items:start}.eyebrow{font-size:.74rem;text-transform:uppercase;letter-spacing:.14em;color:var(--brand);font-weight:800}.hero h1{font-size:clamp(2rem,5vw,3.9rem);line-height:1.04;margin:.4rem 0 1rem}.lead{font-size:1.1rem;color:#44403c;max-width:70ch}.hero-actions{display:flex;gap:.7rem;flex-wrap:wrap;margin-top:1.3rem}
.btn{display:inline-flex;align-items:center;justify-content:center;text-decoration:none;border-radius:0;padding:.68rem 1.05rem;font-weight:700;border:1px solid var(--ink);background:var(--paper);color:var(--ink);cursor:pointer;font:inherit;font-weight:700}.btn--primary{background:var(--brand);border-color:var(--brand);color:#fff}.btn--primary:hover{background:#0c3d20;color:#fff}.btn--ghost{border-color:var(--ink);background:var(--paper);color:var(--ink)}
.quick-panel{background:var(--paper);border:1px solid var(--ink);border-radius:0;box-shadow:none;padding:1rem}.quick-panel h2{margin:-1rem -1rem .85rem;background:var(--brand);color:#f7f3e8;font-family:var(--serif);font-weight:700;font-size:1rem;text-align:center;text-transform:uppercase;letter-spacing:.12em;padding:.62rem .5rem}.quick-panel::after{content:"";display:block;margin:1.1rem -1rem -1rem;border-top:2px dashed var(--line);padding-bottom:.5rem}
.mini-calendar{display:grid;grid-template-columns:repeat(7,1fr);gap:1px;background:var(--line);border:1px solid var(--line)}.mini-calendar span{display:flex;align-items:center;justify-content:center;min-height:34px;border-radius:0;background:var(--paper);font-size:.88rem;font-family:var(--serif);font-weight:600;font-variant-numeric:tabular-nums}.mini-calendar .head{background:var(--bg);color:var(--muted);font-family:var(--sans);font-weight:700}.mini-calendar .empty{background:var(--bg)}.mini-calendar .weekend{background:var(--wk-bg);color:var(--wk-ink)}.mini-calendar .holiday{background:var(--hol-bg);color:var(--hol);font-weight:800}.mini-calendar .special{background:var(--sp-bg);color:var(--sp-ink)}.mini-calendar .today{background:var(--ink);color:var(--bg);font-weight:800;outline:none}
.quick-panel__holidays{margin-top:.85rem}.quick-panel__holidays h3{margin:0 0 .3rem;font-family:var(--sans);font-size:.7rem;text-transform:uppercase;letter-spacing:.12em;color:var(--muted)}.quick-panel__holidays ul{list-style:none;margin:0;padding:0}.quick-panel__holidays li{display:flex;gap:.55rem;padding:.3rem 0;border-top:1px solid var(--line);font-size:.88rem}.quick-panel__holidays li strong{font-variant-numeric:tabular-nums;color:var(--hol)}.quick-panel__nohol{font-size:.86rem;margin:.85rem 0 0}
.section{padding:2.1rem 0}.section-title{display:flex;align-items:end;justify-content:space-between;gap:1rem;margin-bottom:1.05rem;border-top:3px double var(--ink);padding-top:.75rem}.section-title h2{margin:0;font-size:1.5rem}.section-title h2::before{content:"";display:inline-block;width:.5em;height:.5em;background:var(--hol);margin-right:.5rem}.section-title p{margin:.2rem 0 0;color:var(--muted)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(235px,1fr));gap:1rem}.card{background:var(--paper);border:1px solid var(--line);border-radius:var(--radius);padding:1rem;box-shadow:none}a.card{text-decoration:none;color:inherit}a.card:hover{border-color:var(--ink);box-shadow:3px 3px 0 var(--line)}.card h3{margin:.1rem 0 .4rem}.stat{font-family:var(--serif);font-size:2.1rem;font-weight:700;color:var(--brand);margin:.2rem 0;font-variant-numeric:tabular-nums}.muted{color:var(--muted)}.muted-on-dark{color:#b3aca0}
.prose{font-size:1.03rem}.prose h2{margin-top:1.8rem}.prose p,.prose li{color:#3f3a33}.prose li{margin:.35rem 0}
.table-wrap{overflow-x:auto;background:var(--paper);border:1px solid var(--line);border-radius:0}table{border-collapse:collapse;width:100%;min-width:700px}th,td{padding:.68rem .8rem;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}td{font-variant-numeric:tabular-nums}th{background:var(--paper);color:var(--ink);font-size:.74rem;text-transform:uppercase;letter-spacing:.08em;border-bottom:3px double var(--ink)}
.month-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(285px,1fr));gap:1rem}.month{background:var(--paper);border:1px solid var(--line);border-radius:0;padding:.85rem}.month--large{max-width:760px;margin:auto;border:1px solid var(--ink)}.month h3{margin:0 0 .65rem;text-align:center;text-transform:uppercase;letter-spacing:.12em;font-size:.98rem;border-bottom:3px double var(--ink);padding-bottom:.5rem}.month h3 a{color:inherit;text-decoration:none}
.calendar-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:1px;background:var(--line);border:1px solid var(--line)}.calendar-grid span{min-height:32px;display:flex;align-items:center;justify-content:center;border-radius:0;background:var(--paper);font-size:.92rem;font-family:var(--serif);font-weight:600;font-variant-numeric:tabular-nums}.month--large .calendar-grid span{min-height:54px;font-size:1.18rem}.calendar-grid .head{font-family:var(--sans);font-weight:700;background:var(--bg);color:var(--muted)}.calendar-grid .empty{background:var(--bg)}.calendar-grid .weekend{background:var(--wk-bg);color:var(--wk-ink)}.calendar-grid .holiday{background:var(--hol-bg);color:var(--hol);font-weight:800}.calendar-grid .special{background:var(--sp-bg);color:var(--sp-ink)}
.tool{background:var(--paper);border:1px solid var(--line);border-top:3px double var(--ink);border-radius:0;padding:1.05rem;box-shadow:none}.tool-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:.8rem;margin-bottom:1rem}.field label{display:block;font-weight:700;margin-bottom:.25rem}.field input,.field select{width:100%;padding:.66rem .75rem;border:1px solid #8b8378;border-radius:0;font:inherit;background:#fff;color:var(--ink)}
.result-box{margin-top:1rem;background:#f0f5ec;border:1px solid var(--brand);border-left:4px solid var(--brand);border-radius:0;padding:1rem}.notice{background:#fbf3dc;border:1px solid #d9c58a;border-radius:0;padding:1rem;color:#6b4d10}
.donate-card{text-align:center}.donate-qr{display:block;max-width:190px;height:auto;margin:1rem auto 0;border:1px solid var(--line);border-radius:0}
.footer{margin-top:2rem;padding:2rem 0;background:var(--ink);color:#e8e2d9;border-top:4px solid var(--brand)}.footer a{color:#efe9dd}.footer h3{font-size:.92rem;text-transform:uppercase;letter-spacing:.12em;color:#f7f3e8}.footer-grid{display:grid;grid-template-columns:2fr repeat(3,1fr);gap:1rem}.footer ul{list-style:none;padding:0;margin:.4rem 0}.footer li{margin:.25rem 0}
.tag-cloud{display:flex;flex-wrap:wrap;gap:.45rem}.tag-link{display:inline-flex;text-decoration:none;padding:.32rem .6rem;border-radius:0;background:var(--paper);border:1px solid var(--line);font-weight:700;color:var(--brand);font-size:.88rem}.tag-link:hover{border-color:var(--ink)}.tag{display:inline-flex;padding:.16rem .45rem;border-radius:0;background:var(--soft);color:#14532d;font-size:.76rem;font-weight:800;letter-spacing:.02em}
.nav-toggle{display:none;background:transparent;border:1px solid var(--ink);border-radius:0;padding:.45rem .6rem;cursor:pointer;color:var(--ink);font:inherit}.nav-toggle__bars{display:inline-flex;flex-direction:column;gap:4px;width:20px;vertical-align:middle}.nav-toggle__bars span{display:block;height:2px;background:currentColor;border-radius:0}
@media(max-width:780px){.hero-grid{grid-template-columns:1fr}.footer-grid{grid-template-columns:1fr}.section-title{display:block}.table-wrap{overflow-x:auto;-webkit-overflow-scrolling:touch}table{min-width:560px}.main-nav a{font-size:.86rem;padding:.45rem}.month--large .calendar-grid span{min-height:42px;font-size:1rem}.nav-toggle{display:inline-flex;align-items:center;gap:.4rem;font-weight:700}.main-nav{display:none;flex-basis:100%;order:3}.main-nav.is-open{display:block}.main-nav ul{flex-direction:column;gap:0;padding:.4rem 0}.main-nav a{display:block;width:100%;font-size:.95rem;padding:.6rem .3rem;border-bottom:1px solid var(--line)}.main-nav a[aria-current=page]{border-bottom:1px solid var(--line);background:var(--soft);color:var(--ink)}.site-header__inner{flex-wrap:wrap}.hero{padding:1.6rem 0 1.2rem}.hero h1{font-size:clamp(1.7rem,7vw,2.4rem)}.hero+.ad-slot--header{display:none}.hero+.ad-slot--header+.section{padding-top:1rem}}
.calendar-legend{display:flex;flex-wrap:wrap;gap:.55rem .85rem;align-items:center;margin:0 0 1rem;padding:.7rem .85rem;background:var(--paper);border:1px solid var(--line);border-radius:0}.month--large .calendar-legend{margin-top:.35rem}.calendar-legend__item{display:inline-flex;align-items:center;gap:.4rem;color:#4b463f;font-size:.88rem;font-weight:600}.calendar-legend__swatch{width:16px;height:16px;border-radius:0;border:1px solid var(--line);display:inline-block}.calendar-legend__swatch--holiday{background:var(--hol-bg);border-color:var(--hol)}.calendar-legend__swatch--special{background:var(--sp-bg);border-color:#c78a3b}.calendar-legend__swatch--weekend{background:var(--wk-bg);border-color:#c3cad4}.calendar-legend__swatch--today{background:var(--ink);border-color:var(--ink)}
.quick-panel .calendar-legend{margin:.75rem 0 0;padding:.55rem .6rem;gap:.4rem .65rem;border:0;padding-left:0;padding-right:0;background:transparent}.quick-panel .calendar-legend__item{font-size:.76rem}.quick-panel .calendar-legend__swatch{width:12px;height:12px;border-radius:0}
.breadcrumbs{background:var(--paper);border-bottom:1px solid var(--line);padding:.65rem 0;font-size:.88rem;color:var(--muted);margin:0}.breadcrumbs a{color:var(--brand);text-decoration:none;font-weight:700}.breadcrumbs a:hover{text-decoration:underline}.breadcrumbs [aria-current=page]{color:var(--ink);font-weight:700}
.ad-slot{padding:.9rem 0;background:transparent}.ad-slot ins{min-height:90px;display:block;border:1px dashed var(--line);border-radius:0;background:var(--paper);color:var(--muted)}.ad-slot ins:empty::before{content:"Espaço publicitário";display:flex;align-items:center;justify-content:center;height:90px;color:var(--muted);font-size:.85rem;letter-spacing:.04em}.ad-slot--header ins{min-height:100px}.ad-slot--mid ins{min-height:250px}.ad-slot--footer ins{min-height:100px}
.faq{display:flex;flex-direction:column;gap:.6rem}.faq__item{background:var(--paper);border:1px solid var(--line);border-radius:0;padding:.75rem 1rem}.faq__item summary{cursor:pointer;font-weight:700;color:var(--brand);outline:none}.faq__item[open] summary{margin-bottom:.5rem}.faq__item p{margin:.25rem 0 0;color:#3f3a33}
.add-cell{font-size:.84rem;white-space:nowrap}.add-cell a{color:var(--brand);text-decoration:none;font-weight:700}.add-cell a:hover{text-decoration:underline}.export-bar{margin:0 0 1rem;display:flex;align-items:center;gap:.65rem;flex-wrap:wrap}.export-bar .btn{padding:.45rem .9rem;font-size:.92rem}
.field input:focus-visible,.field select:focus-visible,.btn:focus-visible,.tag-link:focus-visible,.main-nav a:focus-visible,a.card:focus-visible,.breadcrumbs a:focus-visible,.faq__item summary:focus-visible{outline:2px solid var(--ink);outline-offset:2px;border-radius:0}
.hero h1{text-wrap:balance}
.btn{transition:background-color .12s ease,border-color .12s ease,box-shadow .12s ease,transform .12s ease}.btn:hover{transform:translate(1px,1px);box-shadow:var(--shadow)}.btn--ghost:hover{background:var(--bg);border-color:var(--ink)}
.card{transition:border-color .12s ease,box-shadow .12s ease}
.calendar-grid span,.mini-calendar span{transition:background-color .12s ease,box-shadow .12s ease}.calendar-grid span[title],.mini-calendar span[title]{cursor:help}.calendar-grid span[title]:hover,.mini-calendar span[title]:hover{box-shadow:inset 0 0 0 2px rgba(28,25,23,.45)}
.calendar-grid .today,.mini-calendar .today{background:var(--ink);color:var(--bg);font-weight:800;outline:none}
tbody tr:nth-child(even) td{background:#f6f1e7}tbody tr:hover td{background:#f1ead9}
@media print{.site-header,.main-nav,.footer,.ad-slot,.no-print,.hero-actions,.faq,.export-bar,.add-cell,.skip-link,.tag-cloud,.breadcrumbs{display:none!important}body{background:#fff;color:#000;font-size:11pt}.section{padding:.4rem 0}.container{width:100%}.hero{padding:0;background:#fff;border:0}.hero h1{font-size:1.4rem}.lead{font-size:1rem;color:#222}.table-wrap{border:0;overflow:visible}table{min-width:0;font-size:10pt}th{background:#eee;color:#000}th:last-child,td:last-child{display:none}.card{break-inside:avoid;box-shadow:none;border-color:#aaa}.notice{background:#fff;border-color:#bbb;color:#000}a{color:#000;text-decoration:none}a[href]:after{content:""}.month-grid{grid-template-columns:repeat(3,1fr);gap:.5rem;page-break-inside:auto}.month{break-inside:avoid;padding:.4rem}}
"""


def today_js_text() -> str:
    return """\
(function(){
  function pad(n){return n<10?'0'+n:''+n;}
  var now=new Date();
  var iso=now.getFullYear()+'-'+pad(now.getMonth()+1)+'-'+pad(now.getDate());

  // --- Mini calendario do quick-panel: se o HTML publicado ficou de um mes
  // anterior (build antigo), re-renderiza para o mes corrente usando
  // CB_CALENDAR_DATA. So em panels marcados data-auto-month (mes corrente);
  // paginas de mes especifico (calendario-junho-2026) mantem o mes delas.
  function rebuildMiniCalendar(){
    var panel=document.querySelector('.quick-panel[data-auto-month]');
    if(!panel||!window.CB_CALENDAR_DATA)return;
    var grid=panel.querySelector('.mini-calendar');
    if(!grid)return;
    var first=grid.querySelector('[data-date]');
    if(!first)return;
    var shown=first.getAttribute('data-date').slice(0,7);
    var cur=iso.slice(0,7);
    if(shown===cur)return; // mes exibido ja e o corrente
    var y=now.getFullYear(),m=now.getMonth(); // m: 0-11
    var yd=window.CB_CALENDAR_DATA.years[String(y)];
    if(!yd)return; // fora do range gerado — mantem como esta
    var hol={},nonwork={};
    for(var i=0;i<yd.holidays.length;i++){hol[yd.holidays[i].date]=yd.holidays[i];}
    for(var j=0;j<(yd.standardExcluded||[]).length;j++){nonwork[yd.standardExcluded[j]]=1;}
    var MESES=['Janeiro','Fevereiro','Mar\\u00e7o','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'];
    var h2=panel.querySelector('h2');
    if(h2)h2.textContent=MESES[m]+' '+y;
    // reconstroi somente os spans de dia (mantem os 7 heads)
    var spans=grid.querySelectorAll('span:not(.head)');
    for(var k=0;k<spans.length;k++)grid.removeChild(spans[k]);
    var firstDay=new Date(Date.UTC(y,m,1));
    var lead=(firstDay.getUTCDay()+6)%7; // seg=0
    var dim=new Date(Date.UTC(y,m+1,0)).getUTCDate();
    var frag=document.createDocumentFragment();
    function span(cls,txt,dateIso,title){
      var s=document.createElement('span');
      if(cls)s.className=cls;
      if(dateIso)s.setAttribute('data-date',dateIso);
      if(title)s.title=title;
      s.textContent=txt||'';
      return s;
    }
    for(var a=0;a<lead;a++)frag.appendChild(span('empty',''));
    for(var d=1;d<=dim;d++){
      var di=y+'-'+pad(m+1)+'-'+pad(d);
      var wd=(lead+d-1)%7;
      var cls=[];
      if(wd>=5)cls.push('weekend');
      var mk=hol[di];
      if(mk&&nonwork[di])cls.push('holiday');
      else if(mk)cls.push('special');
      frag.appendChild(span(cls.join(' '),String(d),di,mk?mk.name:null));
    }
    var tail=(lead+dim)%7;
    if(tail)for(var b=tail;b<7;b++)frag.appendChild(span('empty',''));
    grid.appendChild(frag);
    // lista "Feriados deste mes"
    var box=panel.querySelector('.quick-panel__holidays');
    var noh=panel.querySelector('.quick-panel__nohol');
    var monthHols=[];
    for(var c=0;c<yd.holidays.length;c++){
      if(yd.holidays[c].date.slice(5,7)===pad(m+1))monthHols.push(yd.holidays[c]);
    }
    var htmlOut;
    if(monthHols.length){
      var lis='';
      for(var e=0;e<monthHols.length;e++){
        var hh=monthHols[e];
        lis+='<li><strong>'+hh.date.slice(8,10)+'/'+hh.date.slice(5,7)+'</strong> <span></span></li>';
      }
      var div=document.createElement('div');
      div.className='quick-panel__holidays';
      div.innerHTML='<h3>Feriados deste m\\u00eas</h3><ul>'+lis+'</ul>';
      var its=div.querySelectorAll('li span');
      for(var f=0;f<its.length;f++)its[f].textContent=monthHols[f].name;
      if(box)box.replaceWith(div);else if(noh)noh.replaceWith(div);else panel.appendChild(div);
    }else{
      var p=document.createElement('p');
      p.className='quick-panel__nohol muted';
      p.textContent='Sem feriados nacionais neste m\\u00eas.';
      if(box)box.replaceWith(p);else if(!noh)panel.appendChild(p);
    }
  }
  try{rebuildMiniCalendar();}catch(err){/* mantem HTML original */}

  var nodes=document.querySelectorAll('[data-date]');
  for(var i=0;i<nodes.length;i++){
    var el=nodes[i];
    if(el.getAttribute('data-date')===iso){
      el.classList.add('today');
    }
  }
  // Hamburger menu toggle (mobile)
  var btn=document.querySelector('.nav-toggle');
  var nav=document.getElementById('main-nav');
  if(btn && nav){
    btn.addEventListener('click',function(){
      var open=nav.classList.toggle('is-open');
      btn.setAttribute('aria-expanded',open?'true':'false');
      btn.setAttribute('aria-label',open?'Fechar menu':'Abrir menu');
    });
  }
  // Dynamic countdown for proximo-feriado rows ([data-target-date])
  var targets=document.querySelectorAll('[data-target-date]');
  if(targets.length){
    var today=new Date();
    var todayUTC=Date.UTC(today.getFullYear(),today.getMonth(),today.getDate());
    for(var j=0;j<targets.length;j++){
      var t=targets[j];
      var ds=t.getAttribute('data-target-date');
      var p=(ds||'').split('-');
      if(p.length!==3)continue;
      var tgt=Date.UTC(+p[0],+p[1]-1,+p[2]);
      var diff=Math.round((tgt-todayUTC)/86400000);
      var tpl=t.getAttribute('data-template')||'{n}';
      t.textContent=tpl.replace('{n}',String(diff));
    }
  }
})();
"""


def calendar_tools_js_text() -> str:
    return """\
(function(){
  const data = window.CB_CALENDAR_DATA || {};
  const $ = (id) => document.getElementById(id);
  const fmt = (d) => d.toLocaleDateString('pt-BR', { timeZone: 'UTC' });
  function isoDate(d){ return d.toISOString().slice(0,10); }
  function parse(s){ const p = (s || '').split('-').map(Number); return p.length === 3 ? new Date(Date.UTC(p[0], p[1]-1, p[2])) : null; }
  function addDays(d, n){ const x = new Date(d); x.setUTCDate(x.getUTCDate() + n); return x; }
  function isWeekend(d){ const w = d.getUTCDay(); return w === 0 || w === 6; }
  function excluded(year, mode){
    const y = data.years && data.years[String(year)];
    if (!y) return new Set();
    return new Set(mode === 'bank' ? y.bankExcluded : y.standardExcluded);
  }
  function isUseful(d, mode){
    if (mode === 'corridos') return true;
    if (isWeekend(d)) return false;
    return !excluded(d.getUTCFullYear(), mode).has(isoDate(d));
  }
  function countUseful(start, end, mode, includeStart){
    if (!start || !end) return null;
    let a = start <= end ? start : end;
    const b = start <= end ? end : start;
    let count = 0;
    if (!includeStart) a = addDays(a, 1);
    for (let d = new Date(a); d <= b; d = addDays(d, 1)) {
      if (isUseful(d, mode)) count++;
    }
    return start <= end ? count : -count;
  }
  function addUseful(start, days, mode){
    let d = new Date(start);
    let remaining = Number(days || 0);
    while (remaining > 0) {
      d = addDays(d, 1);
      if (isUseful(d, mode)) remaining--;
    }
    return d;
  }
  function isoWeek(d){
    const tmp = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()));
    const day = tmp.getUTCDay() || 7;
    tmp.setUTCDate(tmp.getUTCDate() + 4 - day);
    const yearStart = new Date(Date.UTC(tmp.getUTCFullYear(), 0, 1));
    return Math.ceil((((tmp - yearStart) / 86400000) + 1) / 7);
  }
  function bootDiff(){
    if (!$('diff-run')) return;
    const today = new Date();
    if (!$('diff-start').value) $('diff-start').value = isoDate(today);
    if (!$('diff-end').value) $('diff-end').value = isoDate(addDays(today, 30));
    $('diff-run').addEventListener('click', () => {
      const start = parse($('diff-start').value), end = parse($('diff-end').value);
      const mode = $('diff-mode').value;
      const inc = $('diff-inclusive') ? $('diff-inclusive').value === 'yes' : false;
      const count = countUseful(start, end, mode, inc);
      const box = $('diff-result');
      box.hidden = false;
      box.innerHTML = count === null ? 'Informe as duas datas.' : `<strong>${count}</strong> dia(s) ${mode === 'corridos' ? 'corrido(s)' : (mode === 'bank' ? 'útil(eis) bancário(s)' : 'útil(eis)')} no intervalo.`;
    });
  }
  function bootAdd(){
    if (!$('add-run')) return;
    const today = new Date();
    if (!$('add-start').value) $('add-start').value = isoDate(today);
    $('add-run').addEventListener('click', () => {
      const start = parse($('add-start').value);
      const days = Number($('add-days').value || 0);
      const mode = $('add-mode').value;
      const box = $('add-result');
      box.hidden = false;
      if (!start || days < 0) { box.textContent = 'Informe uma data e quantidade válida.'; return; }
      const result = addUseful(start, days, mode);
      box.innerHTML = `Resultado: <strong>${fmt(result)}</strong> (${days} dia(s) úteis após ${fmt(start)}).`;
    });
  }
  function bootWeek(){
    if (!$('week-run')) return;
    const today = new Date();
    if (!$('week-date').value) $('week-date').value = isoDate(today);
    $('week-run').addEventListener('click', () => {
      const d = parse($('week-date').value);
      const box = $('week-result');
      box.hidden = false;
      if (!d) { box.textContent = 'Informe uma data.'; return; }
      const names = ['domingo','segunda-feira','terça-feira','quarta-feira','quinta-feira','sexta-feira','sábado'];
      box.innerHTML = `${fmt(d)} cai em <strong>${names[d.getUTCDay()]}</strong> e está na semana ISO <strong>${isoWeek(d)}</strong>.`;
    });
  }
  document.addEventListener('DOMContentLoaded', () => { bootDiff(); bootAdd(); bootWeek(); });
})();
"""


def favicon_svg() -> str:
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="12" fill="#166534"/><rect x="12" y="15" width="40" height="37" rx="5" fill="#fff"/><rect x="12" y="15" width="40" height="10" rx="5" fill="#14532d"/><path d="M20 34h8v8h-8zm14 0h8v8h-8z" fill="#166534"/></svg>'


def brand_svg_inline() -> str:
    return '<svg class="brand__mark" viewBox="0 0 64 64" aria-hidden="true"><rect width="64" height="64" rx="12" fill="#166534"/><rect x="12" y="15" width="40" height="37" rx="5" fill="#fff"/><rect x="12" y="15" width="40" height="10" rx="5" fill="#14532d"/><path d="M20 34h8v8h-8zm14 0h8v8h-8z" fill="#166534"/></svg>'


def _png_chunk(kind: bytes, data: bytes) -> bytes:
    checksum = zlib.crc32(kind + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", checksum)


def write_png_icon(path: Path, size: int) -> None:
    brand = (22, 101, 52, 255)
    dark = (20, 83, 45, 255)
    white = (255, 255, 255, 255)

    def px(value: float) -> int:
        return round(value * size / 64)

    pixels = [[brand for _ in range(size)] for _ in range(size)]

    def fill_rect(x1: int, y1: int, x2: int, y2: int, color: tuple[int, int, int, int]) -> None:
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(size, x2), min(size, y2)
        for y in range(y1, y2):
            row = pixels[y]
            for x in range(x1, x2):
                row[x] = color

    fill_rect(px(12), px(15), px(52), px(52), white)
    fill_rect(px(12), px(15), px(52), px(25), dark)
    fill_rect(px(20), px(34), px(28), px(42), brand)
    fill_rect(px(34), px(34), px(42), px(42), brand)

    raw = b"".join(b"\x00" + b"".join(bytes(pixel) for pixel in row) for row in pixels)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
        + _png_chunk(b"IDAT", zlib.compress(raw, 9))
        + _png_chunk(b"IEND", b"")
    )
    path.write_bytes(png)


def _og_bitmap_font() -> dict[str, list[list[int]]]:
    raw = {
        "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
        "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
        "C": ["01111", "10000", "10000", "10000", "10000", "10000", "01111"],
        "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
        "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
        "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
        "G": ["01111", "10000", "10000", "10011", "10001", "10001", "01111"],
        "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
        "I": ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
        "J": ["00001", "00001", "00001", "00001", "00001", "10001", "01110"],
        "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
        "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
        "M": ["10001", "11011", "10101", "10001", "10001", "10001", "10001"],
        "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
        "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
        "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
        "Q": ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
        "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
        "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
        "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
        "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
        "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
        "W": ["10001", "10001", "10001", "10001", "10101", "11011", "10001"],
        "X": ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
        "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
        "Z": ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
        ".": ["00000", "00000", "00000", "00000", "00000", "00000", "00100"],
        "-": ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
        " ": ["00000", "00000", "00000", "00000", "00000", "00000", "00000"],
    }
    return {ch: [[1 if c == "1" else 0 for c in row] for row in rows] for ch, rows in raw.items()}


def write_og_image(path: Path) -> None:
    width, height = 1200, 630
    brand = (22, 101, 52, 255)
    dark = (20, 83, 45, 255)
    white = (255, 255, 255, 255)
    cream = (236, 253, 245, 255)

    pixels = [[brand for _ in range(width)] for _ in range(height)]

    def fill_rect(x1: int, y1: int, x2: int, y2: int, color: tuple[int, int, int, int]) -> None:
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(width, x2), min(height, y2)
        for y in range(y1, y2):
            row = pixels[y]
            for x in range(x1, x2):
                row[x] = color

    mark_x, mark_y, mark_size = 80, 180, 270
    fill_rect(mark_x, mark_y, mark_x + mark_size, mark_y + mark_size, white)
    fill_rect(mark_x, mark_y, mark_x + mark_size, mark_y + 60, dark)
    cell = (mark_size - 50) // 7
    for row in range(2):
        for col in range(2):
            cx = mark_x + 25 + col * (cell + 18)
            cy = mark_y + 110 + row * (cell + 18)
            fill_rect(cx, cy, cx + cell, cy + cell, brand)

    fill_rect(420, 110, 1140, 540, cream)
    fill_rect(420, 110, 460, 540, dark)

    font = _og_bitmap_font()

    def draw_text(text: str, x: int, y: int, scale: int, color):
        cursor = x
        for ch in text:
            glyph = font.get(ch.upper()) or font.get(" ")
            for gy, row in enumerate(glyph):
                for gx, bit in enumerate(row):
                    if bit:
                        fill_rect(cursor + gx * scale, y + gy * scale, cursor + (gx + 1) * scale, y + (gy + 1) * scale, color)
            cursor += (len(glyph[0]) + 1) * scale

    draw_text("CALENDARIOBRASILEIRO", 500, 180, 7, dark)
    draw_text("FERIADOS DIAS UTEIS PRAZOS", 500, 310, 5, brand)
    draw_text("CALENDARIO ESTATICO GRATUITO", 500, 400, 5, dark)

    raw = b"".join(b"\x00" + b"".join(bytes(pixel) for pixel in row) for row in pixels)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + _png_chunk(b"IDAT", zlib.compress(raw, 9))
        + _png_chunk(b"IEND", b"")
    )
    path.write_bytes(png)


def site_manifest_json() -> str:
    return json.dumps(
        {
            "name": SITE_NAME_DISPLAY,
            "short_name": "Calendário BR",
            "description": "Calendário brasileiro com feriados, dias úteis e prazos.",
            "start_url": "/",
            "scope": "/",
            "display": "standalone",
            "background_color": "#f6f7f2",
            "theme_color": "#166534",
            "lang": "pt-BR",
            "icons": [
                {"src": "/favicon.svg", "sizes": "64x64", "type": "image/svg+xml"},
                {"src": "/favicon-192.png", "sizes": "192x192", "type": "image/png"},
                {"src": "/favicon-512.png", "sizes": "512x512", "type": "image/png"},
                {"src": "/apple-touch-icon.png", "sizes": "180x180", "type": "image/png"},
            ],
        },
        ensure_ascii=False,
        indent=2,
    ) + "\n"


def cookie_consent_js_text() -> str:
    """Cookie consent banner + Google Consent Mode v2 (see js/cookie-consent.js)."""
    return r'''/* calendariobrasileiro.com.br — cookie consent banner + Google Consent Mode v2 (GDPR/LGPD)
 * Standalone, no dependencies. Stores choice in localStorage as 'cb-consent' = 'granted' | 'denied'.
 */
(function () {
  'use strict';
  var KEY = 'cb-consent';

  /* Google Consent Mode v2: default everything to denied BEFORE any consent decision. */
  window.dataLayer = window.dataLayer || [];
  function gtag() { dataLayer.push(arguments); }
  gtag('consent', 'default', {
    ad_storage: 'denied',
    ad_user_data: 'denied',
    ad_personalization: 'denied',
    analytics_storage: 'denied'
  });

  function grantAll() {
    gtag('consent', 'update', {
      ad_storage: 'granted',
      ad_user_data: 'granted',
      ad_personalization: 'granted'
    });
  }

  function read() {
    try { return localStorage.getItem(KEY); } catch (_) { return null; }
  }
  function write(v) {
    try { localStorage.setItem(KEY, v); } catch (_) {}
  }

  var stored = read();
  if (stored === 'granted') grantAll();

  var CSS = [
    '.cookie-banner{position:fixed;left:0;right:0;bottom:0;z-index:2147483000;',
    'background:var(--c-surface,var(--c-cream-2,#ffffff));color:var(--c-text,#23262d);',
    'border-top:1px solid var(--c-line,#d8dbe2);box-shadow:0 -4px 18px rgba(0,0,0,.12);',
    'padding:14px 16px;font-size:.95rem;line-height:1.45}',
    '.cookie-banner.is-hidden{opacity:0;transform:translateY(8px);transition:opacity .2s ease,transform .2s ease}',
    '.cookie-banner__inner{max-width:960px;margin:0 auto;display:flex;flex-direction:column;gap:10px}',
    '@media (min-width:640px){.cookie-banner__inner{flex-direction:row;align-items:center}}',
    '.cookie-banner__text{margin:0;flex:1}',
    '.cookie-banner__text a{color:inherit;text-decoration:underline}',
    '.cookie-banner__actions{display:flex;gap:8px;flex-shrink:0}',
    '.cookie-banner .cc-btn{cursor:pointer;font:inherit;font-weight:600;border-radius:8px;',
    'padding:8px 16px;border:1px solid var(--c-primary,var(--c-ink,#1f2937))}',
    '.cookie-banner .cc-btn--primary{background:var(--c-primary,var(--c-ink,#1f2937));color:#fff}',
    '.cookie-banner .cc-btn--ghost{background:transparent;color:var(--c-text,#23262d);',
    'border-color:var(--c-line,#9aa1ad)}'
  ].join('');

  function buildBanner() {
    var style = document.createElement('style');
    style.textContent = CSS;
    document.head.appendChild(style);

    var wrap = document.createElement('div');
    wrap.className = 'cookie-banner';
    wrap.setAttribute('role', 'dialog');
    wrap.setAttribute('aria-label', 'Preferências de cookies');
    wrap.innerHTML = [
      '<div class="cookie-banner__inner">',
      '  <p class="cookie-banner__text">Usamos cookies para anúncios (Google AdSense) e para melhorar o site. Saiba mais na nossa ',
      '  <a href="/privacidade.html">política de privacidade</a>.</p>',
      '  <div class="cookie-banner__actions">',
      '    <button type="button" class="cc-btn cc-btn--ghost" data-cookie="deny">Recusar</button>',
      '    <button type="button" class="cc-btn cc-btn--primary" data-cookie="grant">Aceitar</button>',
      '  </div>',
      '</div>'
    ].join('');
    return wrap;
  }

  function init() {
    if (read() === 'granted' || read() === 'denied') return;
    var banner = buildBanner();
    document.body.appendChild(banner);

    banner.addEventListener('click', function (e) {
      var t = e.target.closest('[data-cookie]');
      if (!t) return;
      var action = t.getAttribute('data-cookie');
      write(action === 'grant' ? 'granted' : 'denied');
      if (action === 'grant') grantAll();
      banner.classList.add('is-hidden');
      setTimeout(function () { banner.remove(); }, 250);
      document.dispatchEvent(new CustomEvent('cb:consent', { detail: { value: action } }));
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  window.CookieConsent = { read: read };
})();
'''


def ensure_base_files() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    (ROOT / "css").mkdir(exist_ok=True)
    (ROOT / "js").mkdir(exist_ok=True)
    (ROOT / "img").mkdir(exist_ok=True)

    (ROOT / "css" / "style.css").write_text(css_text(), encoding="utf-8")
    (ROOT / "js" / "calendar-tools.js").write_text(calendar_tools_js_text(), encoding="utf-8")
    (ROOT / "js" / "today.js").write_text(today_js_text(), encoding="utf-8")
    (ROOT / "js" / "cookie-consent.js").write_text(cookie_consent_js_text(), encoding="utf-8")
    (ROOT / "favicon.svg").write_text(favicon_svg(), encoding="utf-8")
    write_png_icon(ROOT / "favicon-16.png", 16)
    write_png_icon(ROOT / "favicon-32.png", 32)
    write_png_icon(ROOT / "favicon-48.png", 48)
    write_png_icon(ROOT / "favicon-192.png", 192)
    write_png_icon(ROOT / "favicon-512.png", 512)
    write_png_icon(ROOT / "apple-touch-icon.png", 180)
    write_og_image(ROOT / "img" / "og-default.png")

    (ROOT / "site.webmanifest").write_text(site_manifest_json(), encoding="utf-8")
    (ROOT / "ads.txt").write_text("google.com, pub-7516029395999799, DIRECT, f08c47fec0942fa0\n", encoding="utf-8")
    (ROOT / "CNAME").write_text("calendariobrasileiro.com.br\n", encoding="utf-8")
    (ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {DOMAIN}/sitemap.xml\n", encoding="utf-8")


# ----------------------------------------------------------------------------- layout


def json_ld_webpage(title: str, description: str, url: str) -> dict:
    publisher = {
        "@type": "Organization",
        "name": SITE_NAME_DISPLAY,
        "url": DOMAIN + "/",
        "logo": {
            "@type": "ImageObject",
            "url": DOMAIN + "/favicon-512.png",
            "width": 512,
            "height": 512,
        },
    }
    return {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": title,
        "description": description,
        "url": url,
        "inLanguage": "pt-BR",
        "isPartOf": {"@type": "WebSite", "name": SITE_NAME, "url": DOMAIN + "/", "publisher": publisher},
        "publisher": publisher,
    }


def breadcrumb_jsonld(items: list[tuple[str, str]]) -> dict:
    elements = []
    for index, (name, path) in enumerate(items, start=1):
        entry: dict = {"@type": "ListItem", "position": index, "name": name}
        if path:
            entry["item"] = DOMAIN + ("/" if path == "index.html" else f"/{path}")
        elements.append(entry)
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": elements}


def render_breadcrumb_nav(items: list[tuple[str, str]]) -> str:
    parts = []
    for index, (name, path) in enumerate(items):
        if index > 0:
            parts.append('<span aria-hidden="true"> &rsaquo; </span>')
        if path:
            href = "index.html" if path == "index.html" else path
            parts.append(f'<a href="{html.escape(href)}">{html.escape(name)}</a>')
        else:
            parts.append(f'<span aria-current="page">{html.escape(name)}</span>')
    return '<nav class="breadcrumbs" aria-label="Trilha de navegação"><div class="container">' + "".join(parts) + "</div></nav>"


def faq_jsonld(items: list[tuple[str, str]]) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in items
        ],
    }


def render_faq_section(items: list[tuple[str, str]]) -> str:
    rows = "".join(
        f'<details class="faq__item"><summary>{html.escape(q)}</summary><p>{html.escape(a)}</p></details>'
        for q, a in items
    )
    return (
        '<section class="section" id="faq"><div class="container container--narrow">'
        '<div class="section-title"><div><h2>Perguntas frequentes</h2>'
        '<p>Respostas rápidas para as dúvidas mais comuns.</p></div></div>'
        f'<div class="faq">{rows}</div></div></section>'
    )


def ad_slot(position: str) -> str:
    """No-op ad slot.

    Previously this emitted manual ``<ins class="adsbygoogle" data-ad-slot=...>``
    blocks with placeholder slot ids. Those blocks never rendered because the
    slot ids were fictitious. We now rely exclusively on Google AdSense Auto
    Ads, which is activated in the AdSense console: the head-level
    ``<script async ...adsbygoogle.js>`` and ``<meta name="google-adsense-account">``
    tags are enough for Auto Ads to place inventory automatically.

    ``position`` is preserved as an argument so existing call sites do not need
    to change; the return value is intentionally empty.
    """
    del position  # unused; kept for API compatibility
    return ""


HREFLANG_MAP = {
    "index.html": "index.html",
    "dividendos.html": "udbytte.html",
    "numero-da-semana.html": "ugenummer.html",
    "calculadora-idade.html": "aldersberegner.html",
    "diferenca-entre-datas.html": "dato-difference.html",
    "countdown.html": "nedtaelling.html",
    "proximo-feriado.html": "naeste-helligdag.html",
    "dia-da-semana.html": "ugedag.html",
    "data-mais-dias.html": "dato-plus-dage.html",
    "calcular-dias-uteis.html": "beregn-arbejdsdage.html",
    "adicionar-dias-uteis.html": "laeg-arbejdsdage-til.html",
    "subtrair-dias-uteis.html": "traek-arbejdsdage-fra.html",
    "data-da-semana.html": "dato-fra-uge.html",
    "calendario-2026.html": "kalender-2026.html",
    "feriados-2026.html": "helligdage-2026.html",
    "dias-uteis-2026.html": "arbejdsdage-2026.html",
    "melhores-dias-para-folga-2026.html": "bedste-feriedage-2026.html",
    "pascoa-2026.html": "paaske-2026.html",
    "calendario-2027.html": "kalender-2027.html",
    "feriados-2027.html": "helligdage-2027.html",
    "dias-uteis-2027.html": "arbejdsdage-2027.html",
    "melhores-dias-para-folga-2027.html": "bedste-feriedage-2027.html",
    "pascoa-2027.html": "paaske-2027.html",
    "calendario-2028.html": "kalender-2028.html",
    "feriados-2028.html": "helligdage-2028.html",
    "dias-uteis-2028.html": "arbejdsdage-2028.html",
    "melhores-dias-para-folga-2028.html": "bedste-feriedage-2028.html",
    "pascoa-2028.html": "paaske-2028.html",
    "calendario-2029.html": "kalender-2029.html",
    "feriados-2029.html": "helligdage-2029.html",
    "dias-uteis-2029.html": "arbejdsdage-2029.html",
    "melhores-dias-para-folga-2029.html": "bedste-feriedage-2029.html",
    "pascoa-2029.html": "paaske-2029.html",
    "calendario-2030.html": "kalender-2030.html",
    "feriados-2030.html": "helligdage-2030.html",
    "dias-uteis-2030.html": "arbejdsdage-2030.html",
    "melhores-dias-para-folga-2030.html": "bedste-feriedage-2030.html",
    "pascoa-2030.html": "paaske-2030.html",
}

DK_DOMAIN = "https://danskedage.dk"


def hreflang_links(path: str, canonical: str) -> str:
    """Par pt-BR <-> da-DK quando existe pagina equivalente no danskedage."""
    dk = HREFLANG_MAP.get(path)
    if not dk:
        return ""
    dk_url = DK_DOMAIN + ("/" if dk == "index.html" else f"/{dk}")
    return (
        f'<link rel="alternate" hreflang="pt-BR" href="{canonical}">\n'
        f'<link rel="alternate" hreflang="da-DK" href="{dk_url}">\n'
        f'<link rel="alternate" hreflang="x-default" href="{canonical}">\n'
    )


def layout(
    title: str,
    description: str,
    path: str,
    body: str,
    current: str = "",
    breadcrumbs: list[tuple[str, str]] | None = None,
    faq: list[tuple[str, str]] | None = None,
    noindex: bool = False,
) -> str:
    canonical = DOMAIN + ("/" if path == "index.html" else f"/{path}")
    hreflang = hreflang_links(path, canonical)
    og_image = DOMAIN + "/img/og-default.png"
    nav_year = ACTIVE_YEAR
    nav = [
        ("Calendário", f"calendario-{nav_year}.html", "calendario"),
        ("Feriados", f"feriados-{nav_year}.html", "feriados"),
        ("Dias úteis", f"dias-uteis-{nav_year}.html", "dias"),
        ("Bancário", f"feriados-bancarios-{nav_year}.html", "bancario"),
        ("Estados e capitais", "feriados-estaduais.html", "locais"),
        ("Dividendos", "dividendos.html", "dividendos"),
        ("Calculadoras", "calcular-dias-uteis.html", "calc"),
    ]
    nav_html = "".join(
        f'<li><a href="{href}"{(" aria-current=" + chr(34) + "page" + chr(34)) if key == current else ""}>{label}</a></li>'
        for label, href, key in nav
    )

    schema_blocks: list[str] = [
        '<script type="application/ld+json">'
        + json.dumps(json_ld_webpage(title, description, canonical), ensure_ascii=False)
        + "</script>"
    ]
    breadcrumb_html = ""
    if breadcrumbs:
        schema_blocks.append(
            '<script type="application/ld+json">'
            + json.dumps(breadcrumb_jsonld(breadcrumbs), ensure_ascii=False)
            + "</script>"
        )
        breadcrumb_html = render_breadcrumb_nav(breadcrumbs)
    if faq:
        schema_blocks.append(
            '<script type="application/ld+json">'
            + json.dumps(faq_jsonld(faq), ensure_ascii=False)
            + "</script>"
        )

    if breadcrumb_html:
        body = breadcrumb_html + body
    if faq:
        body = body + render_faq_section(faq)

    schema_html = "\n".join(schema_blocks)
    robots_meta = '\n<meta name="robots" content="noindex, follow">' if noindex else ""

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">{robots_meta}
<meta name="google-adsense-account" content="{ADS_CLIENT}">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(description)}">
<link rel="canonical" href="{canonical}">
{hreflang}
<meta name="theme-color" content="#166534">
<meta property="og:type" content="website">
<meta property="og:locale" content="pt_BR">
<meta property="og:site_name" content="{SITE_NAME_DISPLAY}">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(description)}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{og_image}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{html.escape(title)}">
<meta name="twitter:description" content="{html.escape(description)}">
<meta name="twitter:image" content="{og_image}">
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ADS_CLIENT}" crossorigin="anonymous"></script>
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="icon" type="image/png" sizes="16x16" href="/favicon-16.png">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png">
<link rel="icon" type="image/png" sizes="48x48" href="/favicon-48.png">
<link rel="icon" type="image/png" sizes="192x192" href="/favicon-192.png">
<link rel="icon" type="image/png" sizes="512x512" href="/favicon-512.png">
<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
<link rel="stylesheet" href="css/style.css">
<script src="js/cookie-consent.js" defer></script>
{schema_html}
</head>
<body>
<a class="skip-link" href="#conteudo">Pular para o conteúdo</a>
<header class="site-header"><div class="container site-header__inner">
<a class="brand" href="index.html">{brand_svg_inline()}<span>{SITE_NAME_DISPLAY}</span></a>
<button class="nav-toggle" type="button" aria-controls="main-nav" aria-expanded="false" aria-label="Abrir menu"><span class="nav-toggle__bars" aria-hidden="true"><span></span><span></span><span></span></span><span>Menu</span></button>
<nav class="main-nav" id="main-nav" aria-label="Menu principal"><ul>{nav_html}</ul></nav>
</div></header>
<main id="conteudo">{body}</main>
<footer class="footer"><div class="container footer-grid">
<div><a class="brand brand--footer" href="index.html">{brand_svg_inline()}<span>{SITE_NAME_DISPLAY}</span></a><p>Calendários, feriados e dias úteis do Brasil.</p><p class="muted-on-dark">Para uso jurídico, financeiro ou trabalhista, consulte sempre a fonte oficial.</p></div>
<div><h3>Calendário</h3><ul><li><a href="calendario-{nav_year}.html">Calendário {nav_year}</a></li><li><a href="feriados-{nav_year}.html">Feriados {nav_year}</a></li><li><a href="dias-uteis-{nav_year}.html">Dias úteis {nav_year}</a></li><li><a href="melhores-dias-para-folga-{nav_year}.html">Melhores folgas</a></li></ul></div>
<div><h3>Calculadoras</h3><ul><li><a href="calcular-dias-uteis.html">Calcular dias úteis</a></li><li><a href="adicionar-dias-uteis.html">Adicionar dias úteis</a></li><li><a href="subtrair-dias-uteis.html">Subtrair dias úteis</a></li><li><a href="numero-da-semana.html">Número da semana</a></li><li><a href="data-da-semana.html">Data da semana ISO</a></li><li><a href="calculadora-idade.html">Calculadora de idade</a></li><li><a href="diferenca-entre-datas.html">Diferença entre datas</a></li><li><a href="countdown.html">Contagem regressiva</a></li><li><a href="proximo-feriado.html">Próximo feriado</a></li><li><a href="dia-da-semana.html">Dia da semana</a></li><li><a href="data-mais-dias.html">Data ± N dias</a></li><li><a href="calendario-bancario.html">Calendário bancário</a></li></ul></div>
<div><h3>Site</h3><ul><li><a href="sobre.html">Sobre</a></li><li><a href="fontes.html">Fontes</a></li><li><a href="contato.html">Contato</a></li><li><a href="privacidade.html">Privacidade</a></li><li><a href="termos.html">Termos</a></li><li><a href="apoiar.html">Apoiar</a></li><li><a href="sitemap.xml">Sitemap</a></li></ul></div>
</div></footer>
<script src="js/calendar-data.js"></script>
<script src="js/calendar-tools.js"></script>
<script src="js/today.js"></script>
</body>
</html>
"""


def write_page(path: str, title: str, description: str, body: str, current: str = "", breadcrumbs=None, faq=None, noindex: bool = False) -> None:
    (ROOT / path).write_text(layout(title, description, path, body, current, breadcrumbs, faq, noindex=noindex), encoding="utf-8")


# ----------------------------------------------------------------------------- pieces


def month_calendar_html(year: int, month: int, mini: bool = False, uf: str | None = None, city_key: str | None = None) -> str:
    cal = calendar.Calendar(firstweekday=0)
    marks = {h.date: h for h in holidays_for_scope(year, uf, city_key)}
    nonwork = nonwork_dates_for_scope(year, uf, city_key)
    cls = "mini-calendar" if mini else "calendar-grid"
    parts = [f'<div class="{cls}">']
    for wd in WEEKDAYS:
        parts.append(f'<span class="head">{wd}</span>')
    for d in cal.itermonthdates(year, month):
        if d.month != month:
            parts.append('<span class="empty"></span>')
            continue
        classes = []
        if d.weekday() >= 5:
            classes.append("weekend")
        mark = marks.get(d)
        if mark and d in nonwork:
            classes.append("holiday")
        elif mark:
            classes.append("special")
        title_attr = f' title="{html.escape(mark.name)}"' if mark else ""
        parts.append(f'<span class="{" ".join(classes)}" data-date="{iso(d)}"{title_attr}>{d.day}</span>')
    parts.append("</div>")
    return "\n".join(parts)


def quick_panel_holidays_text(year: int, month: int) -> str:
    """Lista textual dos feriados do mes corrente p/ o quick-panel."""
    items: list[Holiday] = []
    for h in national_holidays(year):
        if h.date.month == month:
            items.append(h)
    if not items:
        return '<p class="quick-panel__nohol muted">Sem feriados nacionais neste mês.</p>'
    rows = []
    for h in sorted(items, key=lambda x: x.date):
        rows.append(
            f'<li><strong>{h.date.day:02d}/{h.date.month:02d}</strong> '
            f'<span>{html.escape(h.name)}</span></li>'
        )
    return (
        '<div class="quick-panel__holidays"><h3>Feriados deste mês</h3>'
        f'<ul>{"".join(rows)}</ul></div>'
    )


def mini_month(year: int, month: int, uf: str | None = None, city_key: str | None = None) -> str:
    return (
        f"<h2>{MONTHS[month-1].capitalize()} {year}</h2>"
        + month_calendar_html(year, month, mini=True, uf=uf, city_key=city_key)
        + mini_calendar_legend()
        + quick_panel_holidays_text(year, month)
    )


def hero(
    title: str,
    lead: str,
    eyebrow: str | None = None,
    panel: tuple[int, int] | None = None,
    actions: str | None = None,
    extra: str = "",
) -> str:
    # Quick-panel mostra o mes da pagina quando recebido (ex.: calendario-MES-ANO);
    # caso contrario, cai no mes corrente. Panels de "mes corrente" ganham
    # data-auto-month para que js/today.js os re-renderize client-side quando o
    # HTML publicado ficar de um mes anterior (build antigo em cache/CDN).
    auto_month = panel is None
    if panel is None:
        panel = (date.today().year, date.today().month)
    side = mini_month(panel[0], panel[1])
    auto_attr = ' data-auto-month="1"' if auto_month else ""
    eyebrow = eyebrow or f"Calendário Brasileiro · atualizado para {ACTIVE_YEAR}"
    actions = actions or f'<a class="btn btn--primary" href="calcular-dias-uteis.html">Calcular dias úteis</a><a class="btn btn--ghost" href="feriados-{ACTIVE_YEAR}.html">Ver feriados {ACTIVE_YEAR}</a>'
    return (
        f'<section class="hero"><div class="container hero-grid"><div>'
        f'<span class="eyebrow">{html.escape(eyebrow)}</span>'
        f'<h1>{html.escape(title)}</h1>'
        f'<p class="lead">{html.escape(lead)}</p>'
        f'<div class="hero-actions">{actions}</div>'
        f'{extra}'
        f'</div><aside class="quick-panel"{auto_attr}>{side}</aside></div></section>'
    )


def calendar_legend() -> str:
    return """<div class="calendar-legend" aria-label="Legenda de cores do calendário">
<span class="calendar-legend__item"><span class="calendar-legend__swatch calendar-legend__swatch--holiday"></span>Feriado ou folga considerada</span>
<span class="calendar-legend__item"><span class="calendar-legend__swatch calendar-legend__swatch--special"></span>Data especial</span>
<span class="calendar-legend__item"><span class="calendar-legend__swatch calendar-legend__swatch--weekend"></span>Fim de semana</span>
<span class="calendar-legend__item"><span class="calendar-legend__swatch calendar-legend__swatch--today"></span>Hoje</span>
</div>"""


def mini_calendar_legend() -> str:
    return calendar_legend()


def stats_cards(stats: dict) -> str:
    cards = [
        ("Dias úteis", stats["workdays"], "segunda a sexta menos feriados considerados"),
        ("Feriados em dia útil", stats["holidays_on_weekdays"], "datas que reduzem o expediente padrão"),
        ("Fins de semana", stats["weekend_days"], "sábados e domingos"),
        ("Dias úteis bancários", stats["bank_business_days"], "calendário bancário nacional"),
    ]
    return '<div class="grid">' + "".join(
        f'<article class="card"><h3>{label}</h3><p class="stat">{value}</p><p class="muted">{hint}</p></article>'
        for label, value, hint in cards
    ) + "</div>"


def gcal_link(h: Holiday) -> str:
    start = h.date.strftime("%Y%m%d")
    end = (h.date + timedelta(days=1)).strftime("%Y%m%d")
    text = html.escape(h.name, quote=True).replace(" ", "+")
    details = html.escape(h.kind + (". " + h.note if h.note else ""), quote=True).replace(" ", "+")
    return (
        f"https://calendar.google.com/calendar/u/0/r/eventedit"
        f"?text={text}&dates={start}/{end}&details={details}"
    )


def outlook_link(h: Holiday) -> str:
    start = h.date.strftime("%Y-%m-%d")
    end = (h.date + timedelta(days=1)).strftime("%Y-%m-%d")
    from urllib.parse import quote
    text = quote(h.name)
    body = quote(h.kind + (". " + h.note if h.note else ""))
    return (
        f"https://outlook.live.com/calendar/0/deeplink/compose"
        f"?path=/calendar/action/compose&rru=addevent"
        f"&subject={text}&startdt={start}&enddt={end}&allday=true&body={body}"
    )


def holiday_table(items: list[Holiday]) -> str:
    rows = []
    for h in items:
        gcal = gcal_link(h)
        ol = outlook_link(h)
        rows.append(
            "<tr>"
            f"<td>{fmt_short(h.date)}</td>"
            f"<td>{WEEKDAYS_LONG[h.date.weekday()]}</td>"
            f"<td><strong>{html.escape(h.name)}</strong><br><span class=\"muted\">{html.escape(h.kind)}</span></td>"
            f"<td>{'Sim' if h.official else 'Não / depende'}</td>"
            f"<td>{html.escape(h.note)}</td>"
            f'<td class="add-cell no-print"><a href="{gcal}" target="_blank" rel="nofollow noopener" title="Adicionar ao Google Calendar">GCal</a> · '
            f'<a href="{ol}" target="_blank" rel="nofollow noopener" title="Adicionar ao Outlook">Outlook</a></td>'
            "</tr>"
        )
    return (
        '<div class="table-wrap"><table><thead><tr>'
        '<th>Data</th><th>Dia</th><th>Feriado</th><th>Legal</th><th>Observação</th><th class="no-print">Adicionar</th>'
        '</tr></thead><tbody>' + "".join(rows) + "</tbody></table></div>"
    )


def make_ics(year: int, items: list[Holiday], scope_label: str) -> str:
    """Build an iCalendar (.ics) string with VEVENTs for each holiday."""
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:-//{SITE_NAME}//Feriados {scope_label} {year}//PT",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:Feriados {scope_label} {year}",
        f"X-WR-CALDESC:Feriados nacionais brasileiros — fonte {DOMAIN}",
        "X-WR-TIMEZONE:America/Sao_Paulo",
    ]
    for h in items:
        start = h.date.strftime("%Y%m%d")
        end = (h.date + timedelta(days=1)).strftime("%Y%m%d")
        uid = f"{h.date.isoformat()}-{abs(hash(h.name)) % 10**8}@calendariobrasileiro.com.br"
        summary = h.name.replace(",", "\\,").replace(";", "\\;")
        desc_raw = h.kind + (". " + h.note if h.note else "")
        desc = desc_raw.replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")
        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now}",
            f"DTSTART;VALUE=DATE:{start}",
            f"DTEND;VALUE=DATE:{end}",
            f"SUMMARY:{summary}",
            f"DESCRIPTION:{desc}",
            "TRANSP:TRANSPARENT",
            "STATUS:CONFIRMED",
            "END:VEVENT",
        ])
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def year_overview(year: int) -> str:
    stats = year_stats(year)
    # "Dias úteis (nacional civil)" usa apenas os feriados oficiais da Lei nº 10.607
    # (exclui Sexta-feira Santa e Corpus Christi, que sao religiosos/bancarios).
    national_dates = legal_national_dates(year)
    days = list(daterange(date(year, 1, 1), date(year, 12, 31)))
    workdays_national_only = sum(1 for d in days if d.weekday() < 5 and d not in national_dates)
    nationals_count = sum(1 for h in national_holidays(year) if h.official)
    cards = [
        ("Dias úteis", workdays_national_only, "segunda a sexta menos feriados nacionais civis"),
        ("Feriados nacionais", nationals_count, "feriados civis previstos em lei federal"),
        ("Semanas ISO", stats["iso_weeks"], "semanas no ano calendário"),
        ("Fins de semana", stats["weekend_days"], "sábados e domingos"),
    ]
    return '<div class="grid">' + "".join(
        f'<article class="card"><h3>{label}</h3><p class="stat">{value}</p><p class="muted">{desc}</p></article>'
        for label, value, desc in cards
    ) + "</div>"


def link_grid(year: int) -> str:
    links = [
        (f"Feriados {year}", f"feriados-{year}.html", "Lista nacional com datas, dia da semana e base legal."),
        (f"Dias úteis {year}", f"dias-uteis-{year}.html", "Contagem mês a mês."),
        (f"Feriados bancários {year}", f"feriados-bancarios-{year}.html", "Calendário FEBRABAN/ANBIMA."),
        (f"Melhores folgas {year}", f"melhores-dias-para-folga-{year}.html", "Pontes e emendas de feriado."),
        (f"Carnaval {year}", f"carnaval-{year}.html", "Segunda, terça e quarta de cinzas."),
        (f"Páscoa {year}", f"pascoa-{year}.html", "Semana Santa e Domingo de Páscoa."),
    ]
    return (
        '<section class="section"><div class="container"><div class="grid">'
        + "".join(f'<a class="card" href="{href}"><h3>{title}</h3><p class="muted">{desc}</p></a>' for title, href, desc in links)
        + "</div></div></section>"
    )


def year_calendar_section(year: int) -> str:
    months = []
    for month in range(1, 13):
        slug = MONTH_SLUGS[month - 1]
        months.append(
            f'<section class="month"><h3><a href="calendario-{slug}-{year}.html">{MONTHS[month-1].capitalize()} {year}</a></h3>'
            f'{month_calendar_html(year, month)}</section>'
        )
    return (
        '<section class="section"><div class="container"><div class="section-title"><div>'
        '<h2>Calendário mês a mês</h2>'
        '<p>Vermelho indica feriado/folga; amarelo indica data especial.</p>'
        '</div></div>'
        + calendar_legend()
        + '<div class="month-grid">'
        + "".join(months)
        + "</div></div></section>"
    )


def links_year_nav(prefix: str, label: str, start: int, end: int) -> str:
    links = "".join(f'<a class="tag-link" href="{prefix}-{year}.html">{label} {year}</a>' for year in range(start, end + 1))
    return f'<div class="tag-cloud">{links}</div>'


# ----------------------------------------------------------------------------- renderers


def render_index(year: int) -> None:
    body = hero(
        f"Calendário {year}",
        f"Calendário brasileiro {year}: feriados nacionais, dias úteis, calendário bancário, prazos e datas por estado e capital.",
        eyebrow=f"Calendário Brasileiro · {year}",
        panel=(year, date.today().month if date.today().year == year else 1),
        actions=f'<a class="btn btn--primary" href="calcular-dias-uteis.html">Calcular dias úteis</a><a class="btn btn--ghost" href="feriados-{year}.html">Ver feriados {year}</a>',
    )
    body += ad_slot("header")
    body += '<section class="section"><div class="container"><div class="section-title"><div><h2>Resumo de ' + str(year) + '</h2><p>Contagem nacional padrão.</p></div></div>'
    body += year_overview(year)
    body += '</div></section>'
    body += link_grid(year)
    body += ad_slot("mid")
    body += year_calendar_section(year)
    body += ad_slot("footer")
    write_page(
        "index.html",
        f"Calendário {year} - feriados, dias úteis e prazos no Brasil",
        f"Calendário brasileiro {year} com feriados, dias úteis, calendário bancário, prazos e datas por estados e capitais.",
        body,
        "calendario",
    )


def render_year(year: int) -> None:
    stats = year_stats(year)
    body = hero(
        f"Calendário {year}",
        f"Calendário {year} no Brasil com feriados, dias úteis, Páscoa, Carnaval, Corpus Christi, calendário bancário e melhores folgas.",
        panel=(year, 1),
        actions=f'<a class="btn btn--primary" href="feriados-{year}.html">Feriados {year}</a><a class="btn btn--ghost" href="dias-uteis-{year}.html">Dias úteis {year}</a>',
    )
    body += ad_slot("header")
    body += '<section class="section"><div class="container">' + year_overview(year) + '</div></section>'
    body += link_grid(year)
    body += ad_slot("mid")
    body += year_calendar_section(year)
    body += ad_slot("footer")
    write_page(
        f"calendario-{year}.html",
        f"Calendário {year} - Brasil",
        f"Calendário brasileiro {year}: {stats['workdays']} dias úteis, {stats['holidays']} feriados considerados e {stats['iso_weeks']} semanas ISO.",
        body,
        "calendario",
        breadcrumbs=[("Início", "index.html"), ("Calendário", f"calendario-{ACTIVE_YEAR}.html"), (str(year), "")],
    )


def render_month_pages(year: int) -> None:
    for month in range(1, 13):
        month_name = MONTHS[month - 1]
        slug = MONTH_SLUGS[month - 1]
        month_items = [h for h in national_holidays(year) if h.date.month == month]
        body = hero(
            f"Calendário de {month_name} de {year}",
            f"Dias do mês, fins de semana, feriados e datas especiais de {month_name} de {year}.",
            panel=(year, month),
            actions=f'<a class="btn btn--primary" href="calendario-{year}.html">Calendário {year}</a><a class="btn btn--ghost" href="dias-uteis-{year}.html">Dias úteis</a>',
        )
        body += ad_slot("header")
        body += (
            f'<section class="section"><div class="container"><section class="month month--large">'
            f'<h2>{month_name.capitalize()} {year}</h2>'
            f'{calendar_legend()}{month_calendar_html(year, month)}</section></div></section>'
        )
        if month_items:
            body += (
                f'<section class="section"><div class="container">'
                f'<h2>Feriados e datas de {month_name} de {year}</h2>{holiday_table(month_items)}</div></section>'
            )
        else:
            body += '<section class="section"><div class="container"><div class="notice">Sem feriado nacional neste mês. Verifique feriados estaduais e municipais da sua cidade.</div></div></section>'
        body += ad_slot("mid")
        write_page(
            f"calendario-{slug}-{year}.html",
            f"Calendário de {month_name} de {year}",
            f"Calendário de {month_name} de {year} no Brasil, com feriados e dias úteis.",
            body,
            "calendario",
            breadcrumbs=[
                ("Início", "index.html"),
                ("Calendário", f"calendario-{ACTIVE_YEAR}.html"),
                (str(year), f"calendario-{year}.html"),
                (month_name.capitalize(), ""),
            ],
        )


def render_holidays(year: int) -> None:
    items = national_holidays(year)
    e = easter_sunday(year)
    body = hero(
        f"Feriados {year}",
        f"Feriados nacionais, datas móveis e datas comuns do calendário brasileiro em {year}, com base legal e observações.",
        panel=(year, 1),
        actions=f'<a class="btn btn--primary" href="calendario-{year}.html">Ver calendário</a><a class="btn btn--ghost" href="feriados-bancarios-{year}.html">Feriados bancários</a>',
    )
    body += ad_slot("header")
    ics_name = f"feriados-{year}.ics"
    (ROOT / ics_name).write_text(make_ics(year, items, "Brasil"), encoding="utf-8")
    download_box = (
        f'<p class="export-bar no-print">'
        f'<a class="btn btn--ghost" href="{ics_name}" download>↓ Baixar .ics ({year})</a> '
        f'<span class="muted">Importe no Google Calendar, Apple Calendar, Outlook, etc.</span></p>'
    )
    body += f'<section class="section"><div class="container"><h2>Feriados nacionais e datas móveis de {year}</h2>{download_box}{holiday_table(items)}<p class="notice">Carnaval, Corpus Christi e Sexta-feira Santa têm tratamento específico: podem não ser feriado nacional civil mas aparecem em calendários bancários e municipais.</p></div></section>'
    body += ad_slot("mid")
    faq = [
        (f"Quantos feriados nacionais existem em {year}?", f"Em {year} há {sum(1 for h in items if h.official)} feriados nacionais civis no Brasil, contando todas as datas legais previstas em lei federal."),
        (f"Quando cai a Páscoa em {year}?", f"A Páscoa cai em {fmt_date(e)} ({WEEKDAYS_LONG[e.weekday()]}). Sexta-feira Santa é {fmt_date(e - timedelta(days=2))}."),
        (f"Quando é o Carnaval em {year}?", f"O Carnaval de {year} ocorre na segunda {fmt_date(e - timedelta(days=48))} e na terça {fmt_date(e - timedelta(days=47))}, com Quarta-feira de Cinzas em {fmt_date(e - timedelta(days=46))}."),
        (f"Quando é Corpus Christi em {year}?", f"Corpus Christi cai em {fmt_date(e + timedelta(days=60))} ({WEEKDAYS_LONG[(e + timedelta(days=60)).weekday()]}). Não é feriado nacional civil mas é feriado bancário e municipal em muitas cidades."),
        ("Carnaval é feriado nacional?", "Não. O Carnaval (segunda e terça) é ponto facultativo no calendário federal e aparece como feriado bancário. Estados e municípios podem decretar feriado próprio."),
        ("Sexta-feira Santa é feriado nacional?", "Sexta-feira Santa não consta na Lei nº 10.607 como feriado nacional civil, mas é feriado religioso adotado pela maioria dos estados e municípios e consta no calendário bancário."),
    ]
    body += f'<section class="section"><div class="container"><h2>Outros anos</h2>{links_year_nav("feriados", "Feriados", START_YEAR_DEFAULT, END_YEAR_DEFAULT)}</div></section>'
    write_page(
        f"feriados-{year}.html",
        f"Feriados {year} no Brasil",
        f"Feriados nacionais {year}, datas móveis, Carnaval, Páscoa, Corpus Christi e base legal.",
        body,
        "feriados",
        breadcrumbs=[("Início", "index.html"), ("Feriados", f"feriados-{ACTIVE_YEAR}.html"), (str(year), "")],
        faq=faq,
    )


def render_banking(year: int) -> None:
    items = banking_holidays(year)
    body = hero(
        f"Feriados bancários {year}",
        f"Calendário bancário nacional de {year}, com feriados sem expediente ao público e datas de expediente especial.",
        panel=(year, 1),
        actions=f'<a class="btn btn--primary" href="calendario-bancario.html">Sobre a regra bancária</a><a class="btn btn--ghost" href="prazos-{year}.html">Prazos {year}</a>',
    )
    body += ad_slot("header")
    body += f'<section class="section"><div class="container"><h2>Calendário bancário {year}</h2>{holiday_table(items)}<p class="notice">Referências: Resolução CMN nº 4.880/2020, FEBRABAN e ANBIMA. O último dia útil bancário do ano fica sem atendimento ao público.</p></div></section>'
    body += ad_slot("mid")
    write_page(
        f"feriados-bancarios-{year}.html",
        f"Feriados bancários {year}",
        f"Feriados bancários {year} no Brasil e datas com expediente especial.",
        body,
        "bancario",
        breadcrumbs=[("Início", "index.html"), ("Bancário", f"feriados-bancarios-{ACTIVE_YEAR}.html"), (str(year), "")],
    )


def render_workdays(year: int) -> None:
    rows = []
    for month in range(1, 13):
        days = list(daterange(date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])))
        work = sum(1 for d in days if is_workday(d))
        bank = sum(1 for d in days if is_bank_business_day(d))
        rows.append(f"<tr><td>{MONTHS[month-1].capitalize()}</td><td>{len(days)}</td><td>{sum(1 for d in days if d.weekday() >= 5)}</td><td>{work}</td><td>{bank}</td></tr>")
    stats = year_stats(year)
    body = hero(
        f"Dias úteis {year}",
        f"Quantidade de dias úteis em {year}, mês a mês, considerando segunda a sexta e feriados nacionais.",
        panel=(year, 1),
        actions='<a class="btn btn--primary" href="calcular-dias-uteis.html">Calcular intervalo</a><a class="btn btn--ghost" href="adicionar-dias-uteis.html">Adicionar dias úteis</a>',
    )
    body += ad_slot("header")
    body += f'<section class="section"><div class="container">{stats_cards(stats)}</div></section>'
    body += ad_slot("mid")
    body += '<section class="section"><div class="container"><h2>Dias úteis por mês</h2><div class="table-wrap"><table><thead><tr><th>Mês</th><th>Dias corridos</th><th>Fim de semana</th><th>Dias úteis padrão</th><th>Dias úteis bancários</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table></div></div></section>"
    body += '<section class="section"><div class="container"><div class="notice">A contagem nacional não substitui regras contratuais. Feriados estaduais, municipais, forenses e bancários podem alterar prazos.</div></div></section>'
    write_page(
        f"dias-uteis-{year}.html",
        f"Dias úteis {year} - Brasil",
        f"Quantidade de dias úteis em {year} no Brasil, por mês e no ano.",
        body,
        "dias",
        breadcrumbs=[("Início", "index.html"), ("Dias úteis", f"dias-uteis-{ACTIVE_YEAR}.html"), (str(year), "")],
    )


def render_deadlines(year: int) -> None:
    body = hero(
        f"Prazos em {year}",
        f"Guia para contar prazos corridos, dias úteis nacionais e dias úteis bancários em {year}.",
        panel=(year, 1),
        actions='<a class="btn btn--primary" href="calcular-dias-uteis.html">Calcular dias úteis</a><a class="btn btn--ghost" href="adicionar-dias-uteis.html">Adicionar prazo</a>',
    )
    body += ad_slot("header")
    body += """<section class="section"><div class="container container--narrow prose">
<h2>Como usar este calendário para prazos</h2>
<p>Antes de contar um prazo, defina se ele é em dias corridos, dias úteis padrão ou dias úteis bancários.</p>
<ul>
<li><strong>Dias corridos:</strong> contam todos os dias, inclusive fins de semana e feriados.</li>
<li><strong>Dias úteis padrão:</strong> segunda a sexta, excluindo feriados nacionais e datas comuns como Sexta-feira Santa e Corpus Christi.</li>
<li><strong>Dias úteis bancários:</strong> seguem o calendário FEBRABAN/ANBIMA, incluindo Carnaval, Corpus Christi e o último dia útil sem atendimento.</li>
<li><strong>Prazos locais:</strong> podem depender de feriados estaduais, municipais, forenses ou norma específica.</li>
</ul>
<p>Para uso jurídico, tributário, trabalhista ou regulatório, confirme sempre a regra aplicável.</p>
</div></section>"""
    body += ad_slot("mid")
    body += f'<section class="section"><div class="container"><h2>Datas bancárias que afetam prazos em {year}</h2>{holiday_table(banking_holidays(year))}</div></section>'
    write_page(
        f"prazos-{year}.html",
        f"Prazos {year} - dias úteis, bancários e corridos",
        f"Como contar prazos em {year}: dias corridos, úteis, bancários e feriados.",
        body,
        "dias",
        breadcrumbs=[("Início", "index.html"), ("Dias úteis", f"dias-uteis-{ACTIVE_YEAR}.html"), (f"Prazos {year}", "")],
    )


def render_vacation(year: int) -> None:
    rows = "".join(
        f"<tr><td>{fmt_short(item['start'])} – {fmt_short(item['end'])}</td><td>{item['days_off']}</td><td>{item['vacation_days']}</td><td>{html.escape(item['holidays'])}</td><td>{item['ratio']:.1f}x</td></tr>"
        for item in build_best_vacation_windows(year)
    )
    body = hero(
        f"Melhores dias para folga em {year}",
        f"Sugestões para emendar feriados nacionais e fins de semana em {year} gastando menos dias de férias.",
        panel=(year, 1),
        actions=f'<a class="btn btn--primary" href="calendario-{year}.html">Calendário {year}</a><a class="btn btn--ghost" href="feriados-{year}.html">Feriados {year}</a>',
    )
    body += ad_slot("header")
    body += f'<section class="section"><div class="container"><h2>Janelas com melhor relação</h2><div class="table-wrap"><table><thead><tr><th>Período</th><th>Dias de folga</th><th>Dias úteis usados</th><th>Feriado no período</th><th>Ganho</th></tr></thead><tbody>{rows}</tbody></table></div><p class="notice">Sugestão usa apenas o calendário nacional. Feriados estaduais, municipais e políticas internas podem melhorar a relação.</p></div></section>'
    body += ad_slot("mid")
    write_page(
        f"melhores-dias-para-folga-{year}.html",
        f"Melhores dias para tirar folga em {year}",
        f"Pontes e emendas de feriado em {year} para usar menos dias de férias.",
        body,
        "calendario",
        breadcrumbs=[("Início", "index.html"), ("Calendário", f"calendario-{ACTIVE_YEAR}.html"), (f"Melhores folgas {year}", "")],
    )


def render_event_page(year: int, name: str, slug: str, rows: list[tuple[str, date]], note: str, panel_month: int, faq: list[tuple[str, str]]) -> None:
    table = "".join(
        f"<tr><td>{label}</td><td>{fmt_short(d)}</td><td>{WEEKDAYS_LONG[d.weekday()]}</td></tr>"
        for label, d in rows
    )
    body = hero(
        f"{name} {year}",
        f"Datas de {name.lower()} em {year}. {note}",
        panel=(year, panel_month),
        actions=f'<a class="btn btn--primary" href="calendario-{year}.html">Calendário {year}</a><a class="btn btn--ghost" href="feriados-{year}.html">Feriados</a>',
    )
    body += ad_slot("header")
    body += f'<section class="section"><div class="container"><h2>Datas relacionadas</h2><div class="table-wrap"><table><thead><tr><th>Dia</th><th>Data</th><th>Dia da semana</th></tr></thead><tbody>{table}</tbody></table></div></div></section>'
    body += ad_slot("mid")
    write_page(
        f"{slug}-{year}.html",
        f"{name} {year} - data no Brasil",
        f"{name} {year} no calendário brasileiro: data, dia da semana e dúvidas comuns.",
        body,
        "feriados",
        breadcrumbs=[("Início", "index.html"), ("Feriados", f"feriados-{ACTIVE_YEAR}.html"), (name, ""), (str(year), "")],
        faq=faq,
    )


def render_movable(year: int) -> None:
    e = easter_sunday(year)
    seg = e - timedelta(days=48)
    ter = e - timedelta(days=47)
    qua = e - timedelta(days=46)
    sexta_santa = e - timedelta(days=2)
    corpus = e + timedelta(days=60)

    carnaval_faq = [
        (f"Quando é o Carnaval em {year}?", f"A segunda-feira de Carnaval é {fmt_date(seg)} e a terça-feira é {fmt_date(ter)}. A Quarta-feira de Cinzas é {fmt_date(qua)}."),
        ("Carnaval é feriado nacional?", "Não. O Carnaval é ponto facultativo no calendário federal e feriado bancário. Estados e municípios podem decretar feriado próprio."),
        ("Como o Carnaval é calculado?", "O Carnaval é 47 dias antes do Domingo de Páscoa. A terça-feira de Carnaval é 47 dias antes da Páscoa, e a segunda 48."),
        ("Bancos abrem na Quarta-feira de Cinzas?", "Sim, com expediente parcial a partir das 12h, conforme orientação FEBRABAN."),
    ]
    render_event_page(
        year, "Carnaval", "carnaval",
        [("Segunda-feira de Carnaval", seg), ("Terça-feira de Carnaval", ter), ("Quarta-feira de Cinzas", qua)],
        "Carnaval é ponto facultativo nacional e feriado bancário.",
        seg.month, carnaval_faq,
    )

    pascoa_faq = [
        (f"Quando é a Páscoa em {year}?", f"A Páscoa cai em {fmt_date(e)} ({WEEKDAYS_LONG[e.weekday()]}). Sexta-feira Santa é {fmt_date(sexta_santa)}."),
        ("Páscoa é feriado nacional?", "A Páscoa em si (Domingo) cai sempre em domingo. Sexta-feira Santa é feriado religioso adotado por estados e municípios e consta no calendário bancário."),
        ("Como a Páscoa é calculada?", "Usamos a regra gregoriana: a Páscoa é o primeiro domingo depois da primeira lua cheia após o equinócio de março. Aplicamos o algoritmo de Meeus/Jones/Butcher."),
        ("A Sexta-feira Santa é feriado?", "Não consta como feriado nacional civil na Lei nº 10.607, mas é feriado religioso na maioria dos estados e municípios e feriado bancário nacional."),
    ]
    render_event_page(
        year, "Páscoa", "pascoa",
        [("Sexta-feira Santa", sexta_santa), ("Domingo de Páscoa", e), ("Segunda-feira da Páscoa", e + timedelta(days=1))],
        "Páscoa em domingo, com Sexta-feira Santa como feriado religioso comum.",
        e.month, pascoa_faq,
    )

    corpus_faq = [
        (f"Quando é Corpus Christi em {year}?", f"Corpus Christi cai em {fmt_date(corpus)} ({WEEKDAYS_LONG[corpus.weekday()]})."),
        ("Corpus Christi é feriado nacional?", "Não no calendário federal civil, mas é feriado bancário nacional e feriado municipal em grande parte das cidades brasileiras."),
        ("Quantos dias após a Páscoa é Corpus Christi?", "Corpus Christi cai 60 dias depois do Domingo de Páscoa, sempre numa quinta-feira."),
        ("Tem expediente nos bancos em Corpus Christi?", "Não. Corpus Christi consta no calendário FEBRABAN como feriado bancário sem atendimento."),
    ]
    render_event_page(
        year, "Corpus Christi", "corpus-christi",
        [("Corpus Christi", corpus)],
        "Corpus Christi cai 60 dias após o Domingo de Páscoa.",
        corpus.month, corpus_faq,
    )


def render_state_pages(year: int) -> None:
    for state in STATES:
        uf = state["uf"]
        items = holidays_for_scope(year, uf=uf)
        stats = year_stats(year, uf=uf)
        body = hero(
            f"Feriados em {state['name']} em {year}",
            f"Feriados nacionais e datas estaduais cadastradas para {state['name']} em {year}.",
            panel=(year, 1),
            actions=f'<a class="btn btn--primary" href="dias-uteis-{state["slug"]}-{year}.html">Dias úteis no estado</a><a class="btn btn--ghost" href="feriados-estaduais.html">Outros estados</a>',
        )
        body += ad_slot("header")
        body += f'<section class="section"><div class="container">{stats_cards(stats)}</div></section>'
        body += ad_slot("mid")
        body += f'<section class="section"><div class="container"><h2>Lista de feriados</h2>{holiday_table(items)}<p class="notice">Datas estaduais devem ser confirmadas na legislação local em usos formais.</p></div></section>'
        write_page(
            f"feriados-estado-{state['slug']}-{year}.html",
            f"Feriados estaduais em {state['name']} {year} - todas as cidades",
            f"Feriados estaduais e nacionais em {state['name']} em {year}, válidos para todas as cidades do estado.",
            body,
            "locais",
            breadcrumbs=[("Início", "index.html"), ("Estados e capitais", "feriados-estaduais.html"), (state["name"], ""), (str(year), "")],
        )

        rows = []
        for month in range(1, 13):
            days = list(daterange(date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])))
            rows.append(f"<tr><td>{MONTHS[month-1].capitalize()}</td><td>{sum(1 for d in days if is_workday(d, uf=uf))}</td><td>{sum(1 for d in days if d.weekday() >= 5)}</td></tr>")
        body = hero(
            f"Dias úteis em {state['name']} em {year}",
            f"Contagem mensal de dias úteis em {state['name']} considerando feriados nacionais e estaduais.",
            panel=(year, 1),
            actions=f'<a class="btn btn--primary" href="feriados-estado-{state["slug"]}-{year}.html">Feriados no estado</a><a class="btn btn--ghost" href="calcular-dias-uteis.html">Calculadora</a>',
        )
        body += ad_slot("header")
        body += '<section class="section"><div class="container"><div class="table-wrap"><table><thead><tr><th>Mês</th><th>Dias úteis</th><th>Fins de semana</th></tr></thead><tbody>' + "".join(rows) + '</tbody></table></div><p class="notice">Esta contagem usa feriados nacionais + estaduais cadastrados. Para uso formal, confirme legislação local.</p></div></section>'
        body += ad_slot("mid")
        write_page(
            f"dias-uteis-{state['slug']}-{year}.html",
            f"Dias úteis estaduais em {state['name']} {year} - contagem por mês",
            f"Dias úteis em {state['name']} ({uf}) em {year}, mês a mês, considerando feriados nacionais e estaduais.",
            body,
            "dias",
            breadcrumbs=[("Início", "index.html"), ("Dias úteis", f"dias-uteis-{ACTIVE_YEAR}.html"), (state["name"], ""), (str(year), "")],
        )

        city_key = f"{state['capital_slug']}-{uf.lower()}"
        city_items = holidays_for_scope(year, uf=uf, city_key=city_key)
        city_stats = year_stats(year, uf=uf, city_key=city_key)
        city_file = f"feriados-{state['capital_slug']}-{uf.lower()}-{year}.html"
        body = hero(
            f"Feriados em {state['capital']} - {uf} em {year}",
            f"Feriados nacionais, estaduais e municipais cadastrados para {state['capital']} em {year}.",
            panel=(year, 1),
            actions=f'<a class="btn btn--primary" href="dias-uteis-{state["capital_slug"]}-{uf.lower()}-{year}.html">Dias úteis na cidade</a><a class="btn btn--ghost" href="feriados-estaduais.html">Outras capitais</a>',
        )
        body += ad_slot("header")
        body += f'<section class="section"><div class="container">{stats_cards(city_stats)}</div></section>'
        body += ad_slot("mid")
        body += f'<section class="section"><div class="container"><h2>Lista de feriados em {state["capital"]}</h2>{holiday_table(city_items)}<p class="notice">Feriados municipais podem mudar por lei ou decreto. Confirme com a prefeitura para uso formal.</p></div></section>'
        write_page(
            city_file,
            f"Feriados em {state['capital']} (capital) {year} - municipais + estaduais + nacionais",
            f"Feriados em {state['capital']} - {uf} em {year}: municipais da capital, estaduais de {state['name']} e nacionais.",
            body,
            "locais",
            breadcrumbs=[("Início", "index.html"), ("Estados e capitais", "feriados-estaduais.html"), (state["capital"], ""), (str(year), "")],
        )

        rows = []
        for month in range(1, 13):
            days = list(daterange(date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])))
            rows.append(f"<tr><td>{MONTHS[month-1].capitalize()}</td><td>{sum(1 for d in days if is_workday(d, uf=uf, city_key=city_key))}</td><td>{sum(1 for d in days if d.weekday() >= 5)}</td></tr>")
        body = hero(
            f"Dias úteis em {state['capital']} - {uf} em {year}",
            f"Contagem mês a mês de dias úteis em {state['capital']} considerando feriados nacionais, estaduais e municipais cadastrados.",
            panel=(year, 1),
            actions=f'<a class="btn btn--primary" href="{city_file}">Feriados na cidade</a><a class="btn btn--ghost" href="calcular-dias-uteis.html">Calculadora</a>',
        )
        body += ad_slot("header")
        body += '<section class="section"><div class="container"><div class="table-wrap"><table><thead><tr><th>Mês</th><th>Dias úteis</th><th>Fins de semana</th></tr></thead><tbody>' + "".join(rows) + '</tbody></table></div><p class="notice">Feriados locais podem depender de decreto anual. Para uso formal, confirme legislação municipal.</p></div></section>'
        body += ad_slot("mid")
        write_page(
            f"dias-uteis-{state['capital_slug']}-{uf.lower()}-{year}.html",
            f"Dias úteis em {state['capital']} (capital) {year} - municipais + estaduais + nacionais",
            f"Dias úteis em {state['capital']} - {uf} em {year}, mês a mês, com feriados municipais, estaduais e nacionais.",
            body,
            "dias",
            breadcrumbs=[("Início", "index.html"), ("Dias úteis", f"dias-uteis-{ACTIVE_YEAR}.html"), (state["capital"], ""), (str(year), "")],
        )


# ----------------------------------------------------------------------------- tools


def render_tools() -> None:
    today_iso = date.today().isoformat()

    diff_tool = (
        f'<div class="tool tool--hero" data-tool="diff">'
        f'<div class="tool-grid"><div class="field"><label for="diff-start">Data inicial</label><input id="diff-start" type="date" value="{today_iso}"></div>'
        f'<div class="field"><label for="diff-end">Data final</label><input id="diff-end" type="date"></div>'
        f'<div class="field"><label for="diff-mode">Calendário</label><select id="diff-mode"><option value="standard">Dias úteis nacionais</option><option value="bank">Dias úteis bancários</option><option value="corridos">Dias corridos</option></select></div>'
        f'<div class="field"><label for="diff-inclusive">Incluir data inicial?</label><select id="diff-inclusive"><option value="no">Não</option><option value="yes">Sim</option></select></div></div>'
        f'<button class="btn btn--primary" id="diff-run" type="button">Calcular</button>'
        f'<div class="result-box" id="diff-result" hidden></div></div>'
    )
    body = hero(
        "Calculadora de dias úteis",
        "Calcule dias úteis entre duas datas usando calendário nacional ou bancário.",
        actions='<a class="btn btn--ghost" href="adicionar-dias-uteis.html">Adicionar dias úteis</a>',
        extra=diff_tool,
    )
    body += ad_slot("header")
    body += ad_slot("mid")
    write_page(
        "calcular-dias-uteis.html",
        "Calculadora de dias úteis",
        "Calcule dias úteis entre duas datas no Brasil, modo nacional e bancário.",
        body,
        "calc",
        breadcrumbs=[("Início", "index.html"), ("Calcular dias úteis", "")],
    )

    add_tool = (
        f'<div class="tool tool--hero" data-tool="add">'
        f'<div class="tool-grid"><div class="field"><label for="add-start">Data inicial</label><input id="add-start" type="date" value="{today_iso}"></div>'
        f'<div class="field"><label for="add-days">Quantidade de dias úteis</label><input id="add-days" type="number" min="0" value="5"></div>'
        f'<div class="field"><label for="add-mode">Calendário</label><select id="add-mode"><option value="standard">Dias úteis nacionais</option><option value="bank">Dias úteis bancários</option></select></div></div>'
        f'<button class="btn btn--primary" id="add-run" type="button">Adicionar</button>'
        f'<div class="result-box" id="add-result" hidden></div></div>'
    )
    body = hero(
        "Adicionar dias úteis a uma data",
        "Some dias úteis a uma data inicial e encontre a data final, com calendário nacional ou bancário.",
        actions='<a class="btn btn--ghost" href="calcular-dias-uteis.html">Calcular intervalo</a>',
        extra=add_tool,
    )
    body += ad_slot("header")
    body += ad_slot("mid")
    write_page(
        "adicionar-dias-uteis.html",
        "Adicionar dias úteis a uma data",
        "Adicione dias úteis a uma data no Brasil e encontre a data final.",
        body,
        "calc",
        breadcrumbs=[("Início", "index.html"), ("Adicionar dias úteis", "")],
    )

    week_tool = (
        f'<div class="tool tool--hero" data-tool="week">'
        f'<div class="tool-grid"><div class="field"><label for="week-date">Data</label><input id="week-date" type="date" value="{today_iso}"></div></div>'
        f'<button class="btn btn--primary" id="week-run" type="button">Ver semana</button>'
        f'<div class="result-box" id="week-result" hidden></div></div>'
    )
    body = hero(
        "Número da semana",
        "Descubra o número da semana ISO de qualquer data e o dia da semana correspondente.",
        actions=f'<a class="btn btn--ghost" href="calendario-{ACTIVE_YEAR}.html">Ver calendário</a>',
        extra=week_tool,
    )
    body += ad_slot("header")
    body += ad_slot("mid")
    write_page(
        "numero-da-semana.html",
        "Número da semana ISO",
        "Encontre o número da semana ISO para uma data no Brasil.",
        body,
        "calc",
        breadcrumbs=[("Início", "index.html"), ("Número da semana", "")],
    )

    body = hero(
        "Calendário bancário",
        "Consulte feriados bancários nacionais, dias úteis bancários e datas com expediente especial.",
        actions=f'<a class="btn btn--primary" href="feriados-bancarios-{ACTIVE_YEAR}.html">Feriados bancários {ACTIVE_YEAR}</a>',
    )
    body += ad_slot("header")
    bank_items = banking_holidays(ACTIVE_YEAR)
    bank_rows = []
    for h in bank_items:
        bank_rows.append(
            "<tr>"
            f"<td>{fmt_short(h.date)}</td>"
            f"<td>{WEEKDAYS_LONG[h.date.weekday()]}</td>"
            f"<td><strong>{html.escape(h.name)}</strong></td>"
            f"<td>{html.escape(h.kind)}</td>"
            "</tr>"
        )
    bank_table = (
        '<div class="table-wrap"><table><thead><tr>'
        '<th>Data</th><th>Dia</th><th>Feriado/expediente</th><th>Categoria</th>'
        '</tr></thead><tbody>' + "".join(bank_rows) + '</tbody></table></div>'
    )
    body += (
        f'<section class="section"><div class="container">'
        f'<h2>Feriados bancários nacionais em {ACTIVE_YEAR}</h2>'
        '<p class="muted">Lista dos dias sem expediente bancário ao público no Brasil, '
        'conforme calendário FEBRABAN. Inclui carnaval, Sexta-feira Santa, Corpus Christi e o último dia útil do ano.</p>'
        f'{bank_table}'
        '<p class="notice">Em datas de expediente especial (ex.: Quarta-feira de Cinzas) bancos podem abrir após as 12h. '
        'Confirme com sua instituição para operações que dependem de liquidação no dia.</p>'
        '</div></section>'
    )
    body += ad_slot("mid")
    body += f'<section class="section"><div class="container"><h2>Anos disponíveis</h2>{links_year_nav("feriados-bancarios", "Bancário", START_YEAR_DEFAULT, END_YEAR_DEFAULT)}</div></section>'
    write_page(
        "calendario-bancario.html",
        "Calendário bancário do Brasil",
        "Calendário bancário brasileiro com feriados e dias úteis bancários.",
        body,
        "bancario",
        breadcrumbs=[("Início", "index.html"), ("Calendário bancário", "")],
    )

    state_cards = "".join(
        f'<a class="card" href="feriados-estado-{state["slug"]}-{ACTIVE_YEAR}.html"><h3>{state["name"]}</h3><p class="muted">Capital: {state["capital"]}. Feriados nacionais + estaduais.</p></a>'
        for state in STATES
    )
    capital_cards = "".join(
        f'<a class="card" href="feriados-{state["capital_slug"]}-{state["uf"].lower()}-{ACTIVE_YEAR}.html"><h3>{state["capital"]} - {state["uf"]}</h3><p class="muted">Feriados na capital.</p></a>'
        for state in STATES
    )
    body = hero(
        "Feriados estaduais e capitais",
        "Páginas por UF e capital com datas locais cadastradas, somadas aos feriados nacionais.",
        actions='<a class="btn btn--primary" href="feriados-estaduais.html#capitais">Ver capitais</a>',
    )
    body += ad_slot("header")
    body += f'<section class="section" id="estados"><div class="container"><h2>Estados</h2><div class="grid">{state_cards}</div></div></section>'
    body += ad_slot("mid")
    body += f'<section class="section" id="capitais"><div class="container"><h2>Capitais</h2><div class="grid">{capital_cards}</div></div></section>'
    write_page(
        "feriados-estaduais.html",
        "Feriados estaduais e capitais do Brasil",
        "Feriados por estado e capital brasileira com datas nacionais e locais cadastradas.",
        body,
        "locais",
        breadcrumbs=[("Início", "index.html"), ("Estados e capitais", "")],
    )


# ----------------------------------------------------------------------------- institutional


def render_about() -> None:
    body = hero(
        "Sobre o Calendário Brasileiro",
        "Organizamos feriados, dias úteis, calendário bancário e datas locais do Brasil em páginas estáticas, rápidas e sem cadastro.",
        actions='<a class="btn btn--primary" href="fontes.html">Ver fontes</a>',
    )
    body += ad_slot("header")
    body += f"""<section class="section"><div class="container container--narrow prose">
<h2>Como trabalhamos</h2>
<p>O site é estático, gerado por script e revisado anualmente com base em fontes públicas. Datas nacionais fixas vêm de leis federais; datas móveis (Páscoa, Carnaval, Corpus Christi) usam o algoritmo gregoriano de Meeus/Jones/Butcher. O calendário bancário segue regras do mercado financeiro (FEBRABAN/ANBIMA). Datas estaduais e municipais são um cadastro prático para consulta inicial.</p>
<p>Não substituímos consulta jurídica, legislação municipal, normas internas de empresa ou calendários oficiais de tribunais.</p>
<h2>Cobertura</h2>
<p>Geramos páginas para o intervalo {START_YEAR_DEFAULT}-{END_YEAR_DEFAULT}, com calendário anual e mensal, feriados nacionais, feriados bancários, dias úteis, prazos, melhores folgas e páginas por estado e capital.</p>
<h2>Atualização</h2>
<p>O conteúdo é regerado automaticamente todo 1º de janeiro via GitHub Actions, mantendo o ano corrente em destaque na navegação.</p>
</div></section>"""
    body += ad_slot("mid")
    write_page(
        "sobre.html",
        f"Sobre o {SITE_NAME_DISPLAY}",
        f"Sobre o {SITE_NAME_DISPLAY}, metodologia, cobertura e regras do site.",
        body,
        breadcrumbs=[("Início", "index.html"), ("Sobre", "")],
    )


def render_sources() -> None:
    sources = [
        ("Lei nº 662/1949 e Lei nº 10.607/2002", "https://www.planalto.gov.br/ccivil_03/leis/l0662.htm", "Lista base de feriados nacionais fixos."),
        ("Lei nº 6.802/1980", "https://www.planalto.gov.br/ccivil_03/leis/l6802.htm", "Feriado nacional de 12 de outubro."),
        ("Lei nº 14.759/2023", "https://www.planalto.gov.br/ccivil_03/_ato2023-2026/2023/lei/L14759.htm", "Feriado nacional de 20 de novembro."),
        ("Lei nº 9.093/1995", "https://www.planalto.gov.br/ccivil_03/leis/l9093.htm", "Regras para feriados civis, estaduais, municipais e religiosos."),
        ("FEBRABAN - feriados bancários", "https://feriadosbancarios.febraban.org.br/", "Feriados bancários e expediente especial."),
        ("ANBIMA - feriados nacionais", "https://www.anbima.com.br/feriados/feriados.asp", "Tabela de feriados nacionais usada pelo mercado financeiro."),
        ("Banco Central - Resolução CMN nº 4.880/2020", "https://www.bcb.gov.br/estabilidadefinanceira/exibenormativo?numero=4880&tipo=Resolu%C3%A7%C3%A3o+CMN", "Dias úteis para operações no mercado financeiro."),
        ("TSE - calendário eleitoral", "https://www.tse.jus.br/eleicoes/calendario-eleitoral", "Datas eleitorais quando aplicáveis."),
    ]
    rows = "".join(f'<tr><td><a href="{url}" rel="noopener" target="_blank">{name}</a></td><td>{desc}</td></tr>' for name, url, desc in sources)
    body = hero(
        "Fontes e metodologia",
        "Fontes públicas usadas para montar os calendários nacionais, bancários e locais.",
        actions='<a class="btn btn--primary" href="contato.html">Reportar correção</a>',
    )
    body += ad_slot("header")
    body += '<section class="section"><div class="container"><div class="table-wrap"><table><thead><tr><th>Fonte</th><th>Uso</th></tr></thead><tbody>' + rows + "</tbody></table></div></div></section>"
    body += ad_slot("mid")
    write_page(
        "fontes.html",
        "Fontes e metodologia",
        f"Fontes oficiais e metodologia do {SITE_NAME_DISPLAY}.",
        body,
        breadcrumbs=[("Início", "index.html"), ("Fontes", "")],
    )


def render_contact() -> None:
    body = hero(
        "Contato",
        "Encontrou uma data incorreta ou quer sugerir melhoria? Fale com a gente.",
        actions=f'<a class="btn btn--primary" href="mailto:{CONTACT_EMAIL}">Enviar e-mail</a>',
    )
    body += ad_slot("header")
    body += f'<section class="section"><div class="container container--narrow prose"><p>E-mail: <a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a></p><p>Ao reportar uma correção, envie o link da fonte oficial (estadual, municipal, bancária ou normativa).</p></div></section>'
    body += ad_slot("mid")
    write_page(
        "contato.html",
        "Contato",
        f"Contato do {SITE_NAME_DISPLAY}.",
        body,
        breadcrumbs=[("Início", "index.html"), ("Contato", "")],
    )


def render_privacy() -> None:
    body = hero("Política de privacidade", "Esta política explica cookies, anúncios e dados de navegação.")
    body += ad_slot("header")
    body += f"""<section class="section"><div class="container container--narrow prose"><p class="muted">Última atualização: {date.today().strftime('%d/%m/%Y')}.</p>
<h2>Cookies e anúncios</h2><p>Podemos usar cookies e tecnologias similares para funcionamento do site, métricas agregadas e anúncios. O Google AdSense pode usar cookies para personalizar ou medir anúncios conforme as políticas do Google.</p>
<h2>Dados pessoais</h2><p>As calculadoras rodam no navegador e não exigem cadastro. Se você enviar e-mail, usaremos as informações apenas para responder.</p>
<h2>Seus direitos</h2><p>Você pode solicitar informações ou remoção de dados de contato pelo e-mail informado na página de contato.</p>
</div></section>"""
    body += ad_slot("mid")
    write_page(
        "privacidade.html",
        "Política de privacidade",
        f"Política de privacidade do {SITE_NAME_DISPLAY}.",
        body,
        breadcrumbs=[("Início", "index.html"), ("Privacidade", "")],
    )


def render_terms() -> None:
    body = hero("Termos de uso", "Condições de uso das ferramentas e calendários.")
    body += ad_slot("header")
    body += f"""<section class="section"><div class="container container--narrow prose"><p class="muted">Última atualização: {date.today().strftime('%d/%m/%Y')}.</p>
<h2>Uso informativo</h2><p>O conteúdo é informativo e pode conter simplificações. Para decisões jurídicas, trabalhistas, fiscais, financeiras ou regulatórias, consulte a fonte oficial e profissionais qualificados.</p>
<h2>Feriados locais</h2><p>Estados e municípios podem alterar datas por lei ou decreto. Páginas locais são referência inicial, não certidão oficial.</p>
<h2>Disponibilidade</h2><p>O site pode ser atualizado, corrigido ou ficar indisponível temporariamente.</p>
</div></section>"""
    body += ad_slot("mid")
    write_page(
        "termos.html",
        "Termos de uso",
        "Termos de uso e aviso de responsabilidade.",
        body,
        breadcrumbs=[("Início", "index.html"), ("Termos", "")],
    )


def render_support() -> None:
    qr = '<img class="donate-qr" src="img/bmc_qr.png" alt="QR-code Buy Me a Coffee" width="190" height="190" loading="lazy">' if (ROOT / "img" / "bmc_qr.png").exists() else ""
    body = hero(
        "Apoie o projeto",
        "Se o Calendário Brasileiro economizou seu tempo, você pode apoiar a manutenção do site.",
        actions=f'<a class="btn btn--primary" href="{BUY_ME_A_COFFEE}" rel="noopener" target="_blank">Buy me a coffee</a>',
    )
    body += ad_slot("header")
    body += f'<section class="section"><div class="container container--narrow"><article class="card donate-card"><h2>Obrigado pelo apoio</h2><p class="muted">A contribuição ajuda a manter as páginas estáticas, revisar fontes e acrescentar novas cidades.</p><a class="btn btn--primary" href="{BUY_ME_A_COFFEE}" rel="noopener" target="_blank">Apoiar no Buy Me a Coffee</a>{qr}</article></div></section>'
    body += ad_slot("mid")
    write_page(
        "apoiar.html",
        f"Apoiar o {SITE_NAME_DISPLAY}",
        f"Apoiar a manutenção do {SITE_NAME_DISPLAY}.",
        body,
        breadcrumbs=[("Início", "index.html"), ("Apoiar", "")],
    )


def render_404() -> None:
    body = hero(
        "Página não encontrada",
        "A página que você tentou acessar não existe ou mudou de endereço.",
        actions='<a class="btn btn--primary" href="index.html">Voltar ao início</a>',
    )
    write_page(
        "404.html",
        "Página não encontrada - 404",
        f"Página não encontrada no {SITE_NAME_DISPLAY}.",
        body,
        noindex=True,
    )


# ----------------------------------------------------------------------------- data + sitemap


def write_calendar_json(year: int) -> None:
    data = {
        "year": year,
        "stats": year_stats(year),
        "holidays": [
            {"date": iso(h.date), "name": h.name, "kind": h.kind, "scope": h.scope, "official": h.official, "note": h.note}
            for h in national_holidays(year)
        ],
        "best_vacation_windows": [
            {
                "start": iso(x["start"]),
                "end": iso(x["end"]),
                "days_off": x["days_off"],
                "vacation_days": x["vacation_days"],
                "ratio": round(x["ratio"], 2),
                "holidays": x["holidays"],
            }
            for x in build_best_vacation_windows(year)
        ],
    }
    (DATA_DIR / f"calendar-{year}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_calendarios_json(start: int, end: int) -> None:
    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "startYear": start,
        "endYear": end,
        "years": {},
    }
    for year in range(start, end + 1):
        payload["years"][str(year)] = {
            "holidays": [
                {"date": iso(h.date), "name": h.name, "kind": h.kind, "scope": h.scope, "official": h.official}
                for h in national_holidays(year)
            ],
            "standardExcluded": sorted(iso(d) for d in standard_nonwork_dates(year)),
            "bankExcluded": sorted(iso(h.date) for h in banking_holidays(year) if h.kind == "feriado bancário"),
        }
    (DATA_DIR / "calendarios.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (ROOT / "js" / "calendar-data.js").write_text(
        "window.CB_CALENDAR_DATA = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )


def write_sitemap(start: int, end: int) -> None:
    today_iso = date.today().isoformat()
    urls: list[str] = ["", "calcular-dias-uteis.html", "adicionar-dias-uteis.html", "subtrair-dias-uteis.html", "numero-da-semana.html", "data-da-semana.html", "calculadora-idade.html", "diferenca-entre-datas.html", "countdown.html", "proximo-feriado.html", "dia-da-semana.html", "data-mais-dias.html", "calendario-bancario.html", "feriados-estaduais.html", "sobre.html", "fontes.html", "contato.html", "privacidade.html", "termos.html", "apoiar.html", "dividendos.html", "artigos/", "artigos/dias-da-semana.html", "artigos/distribuicao-dias-meses.html", "artigos/historia-dos-calendarios.html", "artigos/historia-feriados-brasil.html", "artigos/nomes-dos-meses.html"]
    for year in range(start, end + 1):
        urls.append(f"calendario-{year}.html")
        for slug in MONTH_SLUGS:
            urls.append(f"calendario-{slug}-{year}.html")
        urls.append(f"feriados-{year}.html")
        urls.append(f"feriados-bancarios-{year}.html")
        urls.append(f"dias-uteis-{year}.html")
        urls.append(f"prazos-{year}.html")
        urls.append(f"melhores-dias-para-folga-{year}.html")
        urls.append(f"carnaval-{year}.html")
        urls.append(f"pascoa-{year}.html")
        urls.append(f"corpus-christi-{year}.html")
        for state in STATES:
            urls.append(f"feriados-estado-{state['slug']}-{year}.html")
            urls.append(f"dias-uteis-{state['slug']}-{year}.html")
            urls.append(f"feriados-{state['capital_slug']}-{state['uf'].lower()}-{year}.html")
            urls.append(f"dias-uteis-{state['capital_slug']}-{state['uf'].lower()}-{year}.html")

    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        loc = DOMAIN + ("/" if not u else f"/{u}")
        if not u:
            priority = "1.0"
        elif u.startswith(("calendario-", "feriados-", "dias-uteis-")):
            priority = "0.8"
        else:
            priority = "0.6"
        lines.append(f"<url><loc>{loc}</loc><lastmod>{today_iso}</lastmod><changefreq>yearly</changefreq><priority>{priority}</priority></url>")
    lines.append("</urlset>")
    (ROOT / "sitemap.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_readme(start: int, end: int) -> None:
    text = f"""# {SITE_NAME_DISPLAY}

Static site generated by `tools/generate_site.py`.

Coverage: {start}-{end}.

## Generate

```powershell
python .\\tools\\generate_site.py
```

## Annual cron

`.github/workflows/yearly-regen.yml` regenerates the site every January 1st (00:01 BRT) and commits if anything changed.

## Pages included

- index / calendar / month-of-year pages
- national holidays, banking holidays, business days and deadlines per year
- Carnaval / Páscoa / Corpus Christi pages per year with FAQ schema
- best-vacation-windows pages per year
- per-state and per-capital pages
- interactive calculators
- trust pages (sobre, fontes, contato, privacidade, termos, apoiar) + 404

## Annual review

Each year confirm: national holiday laws, FEBRABAN/ANBIMA calendar, state and capital decrees, electoral calendar (even years).
"""
    (ROOT / "README.md").write_text(text, encoding="utf-8")


# ----------------------------------------------------------------------------- driver


# Paginas hand-authored na raiz que o generator NAO pode apagar/regravar.
HAND_AUTHORED = {"dividendos.html"}


def clean_generated() -> None:
    for path in ROOT.glob("*.html"):
        if path.name in HAND_AUTHORED:
            continue
        path.unlink()
    for path in ROOT.glob("*.xml"):
        path.unlink()


def generate(start: int, end: int) -> None:
    global ACTIVE_YEAR
    ensure_base_files()
    clean_generated()

    ACTIVE_YEAR = min(max(date.today().year, start), end)
    write_calendarios_json(start, end)

    render_index(ACTIVE_YEAR)
    render_tools()
    render_extra_tools(ROOT, layout)
    render_about()
    render_sources()
    render_contact()
    render_privacy()
    render_terms()
    render_support()
    render_404()

    for year in range(start, end + 1):
        render_year(year)
        render_month_pages(year)
        render_holidays(year)
        render_banking(year)
        render_workdays(year)
        render_deadlines(year)
        render_vacation(year)
        render_movable(year)
        render_state_pages(year)
        write_calendar_json(year)

    write_sitemap(start, end)
    write_readme(start, end)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=START_YEAR_DEFAULT)
    parser.add_argument("--end", type=int, default=END_YEAR_DEFAULT)
    args = parser.parse_args()
    if args.end < args.start:
        raise SystemExit("--end must be >= --start")
    generate(args.start, args.end)
    total = len(list(ROOT.glob("*.html")))
    print(f"Generated {SITE_NAME_DISPLAY}: {total} HTML files in {ROOT}")


if __name__ == "__main__":
    main()
