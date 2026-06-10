#!/usr/bin/env python3
"""Generate CalendarioBrasileiro.com.br as a static site.

The site is intentionally dependency-free. Dates that are deterministic
(Easter, Carnaval, Good Friday and Corpus Christi) are calculated by formula.
Local holidays are stored as curated data and should be reviewed once a year,
because states and municipalities can change local calendars.
"""

from __future__ import annotations

import argparse
import calendar
import html
import json
import shutil
import unicodedata
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
DOMAIN = "https://calendariobrasileiro.com.br"
SITE_NAME = "Calendario Brasileiro"
ADS_CLIENT = "ca-pub-7516029395999799"
CONTACT_EMAIL = "calculadoraestatistica@gmail.com"
BUY_ME_A_COFFEE = "https://buymeacoffee.com/calculadoraestatistica"
START_YEAR = 2026
END_YEAR = 2050
ACTIVE_YEAR = 2026

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
WEEKDAYS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
WEEKDAYS_LONG = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]


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

# Curated local dates. These are useful for long-tail pages, but are not a
# substitute for checking state/municipal law in contracts or compliance work.
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


def daterange(start: date, end: date) -> Iterable[date]:
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


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
    holidays = [
        Holiday(date(year, m, d), name, kind, "Brasil", official, note)
        for m, d, name, kind, official, note in fixed
    ]
    holidays.extend(
        [
            Holiday(e - timedelta(days=48), "Carnaval", "ponto facultativo / feriado bancário", "Brasil", False, "Não é feriado nacional civil; aparece no calendário bancário."),
            Holiday(e - timedelta(days=47), "Carnaval", "ponto facultativo / feriado bancário", "Brasil", False, "Não é feriado nacional civil; aparece no calendário bancário."),
            Holiday(e - timedelta(days=46), "Quarta-feira de Cinzas", "expediente especial", "Brasil", False, "Normalmente há expediente parcial em bancos e órgãos."),
            Holiday(e - timedelta(days=2), "Sexta-feira Santa", "feriado religioso comum", "Brasil", False, "Feriado religioso municipal, conforme a tradição local; incluído em calendários nacionais e bancários."),
            Holiday(e, "Páscoa", "data comemorativa", "Brasil", False, "Domingo de Páscoa."),
            Holiday(e + timedelta(days=60), "Corpus Christi", "ponto facultativo / feriado bancário", "Brasil", False, "Não é feriado nacional civil; costuma ser feriado municipal e feriado bancário."),
        ]
    )
    return sorted(holidays, key=lambda item: item.date)


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
    return {item.date for item in national_holidays(year) if item.name in names}


def legal_national_dates(year: int) -> set[date]:
    return {item.date for item in national_holidays(year) if item.official}


def banking_holidays(year: int) -> list[Holiday]:
    e = easter_sunday(year)
    names = {
        "Confraternização Universal",
        "Carnaval",
        "Sexta-feira Santa",
        "Tiradentes",
        "Dia do Trabalho",
        "Corpus Christi",
        "Independência do Brasil",
        "Nossa Senhora Aparecida",
        "Finados",
        "Proclamação da República",
        "Dia Nacional de Zumbi e da Consciência Negra",
        "Natal",
    }
    items = [
        Holiday(item.date, item.name, "feriado bancário", "Brasil", item.name not in {"Carnaval", "Corpus Christi", "Sexta-feira Santa"}, item.note)
        for item in national_holidays(year)
        if item.name in names
    ]
    items.append(Holiday(e - timedelta(days=46), "Quarta-feira de Cinzas", "expediente bancário especial", "Brasil", False, "A FEBRABAN costuma orientar expediente especial."))
    last = date(year, 12, 31)
    while last.weekday() >= 5 or last in {item.date for item in items if item.kind == "feriado bancário"}:
        last -= timedelta(days=1)
    items.append(Holiday(last, "Último dia útil do ano", "sem expediente bancário ao público", "Brasil", False, "Sem atendimento ao público, admitidas operações internas e compensação."))
    return sorted(items, key=lambda item: item.date)


def state_by_uf(uf: str) -> dict:
    return next(item for item in STATES if item["uf"] == uf)


def state_holidays(year: int, uf: str) -> list[Holiday]:
    state = state_by_uf(uf)
    return [
        Holiday(date(year, month, day), name, "feriado estadual / data magna", state["name"], True, "Data local cadastrada; confirme legislação estadual em casos formais.")
        for month, day, name in STATE_HOLIDAYS.get(uf, [])
    ]


def city_holidays(year: int, city_key: str) -> list[Holiday]:
    state = next(item for item in STATES if f"{item['capital_slug']}-{item['uf'].lower()}" == city_key)
    return [
        Holiday(date(year, month, day), name, "feriado municipal / data local", f"{state['capital']} - {state['uf']}", True, "Data local cadastrada; confirme decreto municipal em casos formais.")
        for month, day, name in CITY_HOLIDAYS.get(city_key, [])
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
        dates.update(item.date for item in state_holidays(year, uf))
    if city_key:
        dates.update(item.date for item in city_holidays(year, city_key))
    return dates


def is_workday(d: date, uf: str | None = None, city_key: str | None = None) -> bool:
    return d.weekday() < 5 and d not in nonwork_dates_for_scope(d.year, uf, city_key)


def is_bank_business_day(d: date) -> bool:
    excluded = {item.date for item in banking_holidays(d.year) if item.kind != "expediente bancário especial"}
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
            names = [item.name for item in national_holidays(year) if item.date in days and item.date in standard_nonwork_dates(year)]
            if ratio >= 2 or names:
                candidates.append(
                    {
                        "start": start,
                        "end": end,
                        "days_off": len(days),
                        "vacation_days": len(vacation_days),
                        "ratio": ratio,
                        "holidays": ", ".join(names) if names else "fins de semana",
                    }
                )
    candidates.sort(key=lambda item: (item["ratio"], item["days_off"]), reverse=True)
    picked = []
    used: list[tuple[date, date]] = []
    for item in candidates:
        if any(not (item["end"] < a or item["start"] > b) for a, b in used):
            continue
        picked.append(item)
        used.append((item["start"], item["end"]))
        if len(picked) == 12:
            break
    return sorted(picked, key=lambda item: item["start"])


def render_month(year: int, month: int, uf: str | None = None, city_key: str | None = None, small: bool = False) -> str:
    marks = {item.date: item for item in holidays_for_scope(year, uf, city_key)}
    today = date.today()
    cls = "mini-calendar" if small else "calendar-grid"
    parts = [f'<div class="{cls}">']
    for weekday in WEEKDAYS:
        parts.append(f'<span class="head">{weekday}</span>')
    first = date(year, month, 1)
    _, days_in_month = calendar.monthrange(year, month)
    for _ in range(first.weekday()):
        parts.append('<span class="empty"></span>')
    for day in range(1, days_in_month + 1):
        current = date(year, month, day)
        classes = []
        title = ""
        if current.weekday() >= 5:
            classes.append("weekend")
        if current in marks:
            classes.append("holiday" if current in nonwork_dates_for_scope(year, uf, city_key) else "special")
            title = f' title="{html.escape(marks[current].name)}"'
        if current == today:
            classes.append("today")
        parts.append(f'<span class="{" ".join(classes)}"{title}>{day}</span>')
    remaining = (7 - ((first.weekday() + days_in_month) % 7)) % 7
    for _ in range(remaining):
        parts.append('<span class="empty"></span>')
    parts.append("</div>")
    return "\n".join(parts)


def calendar_legend() -> str:
    return """<div class="calendar-legend" aria-label="Legenda de cores do calendário">
<span class="calendar-legend__item"><span class="calendar-legend__swatch calendar-legend__swatch--holiday"></span>Feriado ou folga considerada</span>
<span class="calendar-legend__item"><span class="calendar-legend__swatch calendar-legend__swatch--special"></span>Data especial</span>
<span class="calendar-legend__item"><span class="calendar-legend__swatch calendar-legend__swatch--weekend"></span>Fim de semana</span>
<span class="calendar-legend__item"><span class="calendar-legend__swatch calendar-legend__swatch--today"></span>Hoje</span>
</div>"""


def holiday_table(items: list[Holiday]) -> str:
    rows = []
    for item in items:
        rows.append(
            "<tr>"
            f"<td>{fmt_short(item.date)}</td>"
            f"<td>{WEEKDAYS_LONG[item.date.weekday()]}</td>"
            f"<td><strong>{html.escape(item.name)}</strong><br><span class=\"muted\">{html.escape(item.kind)}</span></td>"
            f"<td>{html.escape(item.scope)}</td>"
            f"<td>{'Sim' if item.official else 'Não / depende'}</td>"
            f"<td>{html.escape(item.note)}</td>"
            "</tr>"
        )
    return '<div class="table-wrap"><table><thead><tr><th>Data</th><th>Dia</th><th>Feriado</th><th>Âmbito</th><th>Legal</th><th>Observação</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table></div>"


def stats_cards(stats: dict) -> str:
    cards = [
        ("Dias úteis", stats["workdays"], "segunda a sexta menos feriados considerados"),
        ("Feriados em dia útil", stats["holidays_on_weekdays"], "datas que reduzem o expediente padrão"),
        ("Dias de fim de semana", stats["weekend_days"], "sábados e domingos"),
        ("Dias úteis bancários", stats["bank_business_days"], "calendário bancário nacional"),
    ]
    return '<div class="grid">' + "".join(
        f'<article class="card"><h3>{label}</h3><p class="stat">{value}</p><p class="muted">{hint}</p></article>'
        for label, value, hint in cards
    ) + "</div>"


def json_ld(title: str, description: str, path: str, page_type: str = "WebPage") -> str:
    data = {
        "@context": "https://schema.org",
        "@type": page_type,
        "name": title,
        "description": description,
        "url": DOMAIN + path,
        "inLanguage": "pt-BR",
        "isPartOf": {"@type": "WebSite", "name": SITE_NAME, "url": DOMAIN + "/"},
    }
    return json.dumps(data, ensure_ascii=False)


def page(title: str, description: str, body: str, path: str, active: str = "", extra_head: str = "", extra_script: str = "") -> str:
    canonical = DOMAIN + path
    nav = [
        ("Calendário", f"calendario-{ACTIVE_YEAR}.html", "calendario"),
        ("Feriados", f"feriados-{ACTIVE_YEAR}.html", "feriados"),
        ("Dias úteis", f"dias-uteis-{ACTIVE_YEAR}.html", "dias"),
        ("Bancário", f"feriados-bancarios-{ACTIVE_YEAR}.html", "bancario"),
        ("Estados e capitais", "feriados-estaduais.html", "locais"),
        ("Calculadoras", "calcular-dias-uteis.html", "calc"),
    ]
    nav_html = "".join(
        f'<li><a href="{href}"{" aria-current=\"page\"" if key == active else ""}>{label}</a></li>'
        for label, href, key in nav
    )
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(description)}">
<link rel="canonical" href="{canonical}">
<meta name="theme-color" content="#166534">
<meta property="og:type" content="website">
<meta property="og:locale" content="pt_BR">
<meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(description)}">
<meta property="og:url" content="{canonical}">
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ADS_CLIENT}" crossorigin="anonymous"></script>
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="manifest" href="site.webmanifest">
<link rel="stylesheet" href="css/style.css">
<script type="application/ld+json">{json_ld(title, description, path)}</script>
{extra_head}
</head>
<body>
<a class="skip-link" href="#conteudo">Pular para o conteúdo</a>
<header class="site-header"><div class="container site-header__inner">
<a class="brand" href="index.html">{brand_svg()}<span>Calendário Brasileiro</span></a>
<nav class="main-nav" aria-label="Menu principal"><ul>{nav_html}</ul></nav>
</div></header>
<main id="conteudo">{body}</main>
<footer class="footer"><div class="container footer-grid">
<div><a class="brand brand--footer" href="index.html">{brand_svg()}<span>Calendário Brasileiro</span></a><p>Calendários, feriados, dias úteis, calendário bancário e prazos para planejamento no Brasil.</p><p class="muted-on-dark">Datas locais podem mudar por lei estadual, municipal ou decreto. Para uso jurídico, financeiro ou trabalhista, confira a fonte oficial.</p></div>
<div><h3>Calendário</h3><ul><li><a href="calendario-{ACTIVE_YEAR}.html">Calendário {ACTIVE_YEAR}</a></li><li><a href="feriados-{ACTIVE_YEAR}.html">Feriados {ACTIVE_YEAR}</a></li><li><a href="dias-uteis-{ACTIVE_YEAR}.html">Dias úteis {ACTIVE_YEAR}</a></li><li><a href="melhores-dias-para-folga-{ACTIVE_YEAR}.html">Melhores folgas</a></li></ul></div>
<div><h3>Ferramentas</h3><ul><li><a href="calcular-dias-uteis.html">Calcular dias úteis</a></li><li><a href="adicionar-dias-uteis.html">Adicionar dias úteis</a></li><li><a href="numero-da-semana.html">Número da semana</a></li><li><a href="calendario-bancario.html">Calendário bancário</a></li></ul></div>
<div><h3>Site</h3><ul><li><a href="sobre.html">Sobre</a></li><li><a href="fontes.html">Fontes</a></li><li><a href="contato.html">Contato</a></li><li><a href="privacidade.html">Privacidade</a></li><li><a href="termos.html">Termos</a></li><li><a href="apoiar.html">Apoiar</a></li></ul></div>
</div></footer>
<script src="js/calendar-data.js"></script>
<script src="js/calendar-tools.js"></script>
{extra_script}
</body>
</html>
"""


def brand_svg() -> str:
    return '<svg class="brand__mark" viewBox="0 0 64 64" aria-hidden="true"><rect width="64" height="64" rx="12" fill="#166534"/><rect x="12" y="15" width="40" height="37" rx="5" fill="#fff"/><rect x="12" y="15" width="40" height="10" rx="5" fill="#14532d"/><path d="M20 34h8v8h-8zm14 0h8v8h-8z" fill="#166534"/></svg>'


def section_hero(title: str, lead: str, eyebrow: str = "Calendário do Brasil", actions: str = "") -> str:
    return f'<section class="hero"><div class="container hero-grid"><div><span class="eyebrow">{html.escape(eyebrow)}</span><h1>{html.escape(title)}</h1><p class="lead">{html.escape(lead)}</p><div class="hero-actions">{actions}</div></div><aside class="quick-panel"><h2>{MONTHS[0].capitalize()} {ACTIVE_YEAR}</h2>{render_month(ACTIVE_YEAR, 1, small=True)}</aside></div></section>'


def links_year_nav(prefix: str, label: str) -> str:
    links = "".join(f'<a class="tag-link" href="{prefix}-{year}.html">{label} {year}</a>' for year in range(START_YEAR, END_YEAR + 1))
    return f'<div class="tag-cloud">{links}</div>'


def write(path: str, content: str) -> None:
    (ROOT / path).write_text(content, encoding="utf-8", newline="\n")


def generate_index() -> None:
    stats = year_stats(ACTIVE_YEAR)
    body = section_hero(
        f"Calendário {ACTIVE_YEAR}",
        f"Calendário brasileiro de {ACTIVE_YEAR} com feriados nacionais, estaduais, capitais, dias úteis, calendário bancário, prazos e melhores datas para emendar feriados.",
        actions=f'<a class="btn btn--primary" href="calcular-dias-uteis.html">Calcular dias úteis</a><a class="btn btn--ghost" href="feriados-{ACTIVE_YEAR}.html">Ver feriados {ACTIVE_YEAR}</a>',
    )
    body += f'<section class="section"><div class="container"><div class="section-title"><div><h2>Resumo de {ACTIVE_YEAR}</h2><p>Contagem padrão nacional: segunda a sexta, sem feriados nacionais e datas comuns como Sexta-feira Santa e Corpus Christi.</p></div></div>{stats_cards(stats)}</div></section>'
    body += '<section class="section"><div class="container"><div class="section-title"><div><h2>Ferramentas principais</h2><p>Para prazos, boletos, contratos, RH, férias e planejamento financeiro.</p></div></div><div class="grid">'
    cards = [
        ("Calendário anual", f"calendario-{ACTIVE_YEAR}.html", "Veja todos os meses do ano, feriados e fins de semana."),
        ("Feriados nacionais", f"feriados-{ACTIVE_YEAR}.html", "Lista completa com base legal e observações."),
        ("Dias úteis", f"dias-uteis-{ACTIVE_YEAR}.html", "Total por mês e por ano para planejamento."),
        ("Calendário bancário", f"feriados-bancarios-{ACTIVE_YEAR}.html", "Feriados sem expediente bancário e datas especiais."),
        ("Melhores dias para folga", f"melhores-dias-para-folga-{ACTIVE_YEAR}.html", "Sugestões para emendar feriados usando menos férias."),
        ("Estados e capitais", "feriados-estaduais.html", "Páginas por UF e por capital com datas locais cadastradas."),
    ]
    body += "".join(f'<a class="card" href="{href}"><h3>{title}</h3><p class="muted">{desc}</p></a>' for title, href, desc in cards)
    body += "</div></div></section>"
    body += f'<section class="section"><div class="container"><div class="section-title"><div><h2>Calendários até {END_YEAR}</h2><p>Páginas anuais geradas estaticamente para consulta e SEO de cauda longa.</p></div></div>{links_year_nav("calendario", "Calendário")}</div></section>'
    write("index.html", page(f"Calendário {ACTIVE_YEAR} - feriados, dias úteis e prazos", f"Calendário brasileiro {ACTIVE_YEAR} com feriados, dias úteis, calendário bancário, prazos e datas por estados e capitais.", body, "/", "calendario"))


def generate_year_pages(year: int) -> None:
    stats = year_stats(year)
    body = section_hero(
        f"Calendário {year}",
        f"Veja o calendário {year} no Brasil com feriados, dias úteis, número de semanas, Páscoa, Carnaval, Corpus Christi, calendário bancário e sugestões de folga.",
        actions=f'<a class="btn btn--primary" href="feriados-{year}.html">Feriados {year}</a><a class="btn btn--ghost" href="dias-uteis-{year}.html">Dias úteis {year}</a>',
    )
    body += f'<section class="section"><div class="container"><div class="section-title"><div><h2>Resumo de {year}</h2><p>Contagem nacional padrão.</p></div></div>{stats_cards(stats)}</div></section>'
    body += '<section class="section"><div class="container"><div class="grid">'
    for title, href, desc in [
        (f"Feriados {year}", f"feriados-{year}.html", "Lista com datas, dia da semana e base legal."),
        (f"Dias úteis {year}", f"dias-uteis-{year}.html", "Total por mês e no ano."),
        (f"Feriados bancários {year}", f"feriados-bancarios-{year}.html", "Datas sem expediente bancário."),
        (f"Prazos {year}", f"prazos-{year}.html", "Prazos em dias úteis, corridos e bancários."),
        (f"Melhores dias para folga {year}", f"melhores-dias-para-folga-{year}.html", "Pontes e emendas de feriado."),
        (f"Carnaval {year}", f"carnaval-{year}.html", "Datas do Carnaval e Quarta-feira de Cinzas."),
        (f"Páscoa {year}", f"pascoa-{year}.html", "Semana Santa e Domingo de Páscoa."),
        (f"Corpus Christi {year}", f"corpus-christi-{year}.html", "Data e impacto em dias úteis."),
    ]:
        body += f'<a class="card" href="{href}"><h3>{title}</h3><p class="muted">{desc}</p></a>'
    body += "</div></div></section>"
    body += '<section class="section"><div class="container"><div class="section-title"><div><h2>Calendário mês a mês</h2><p>Vermelho indica feriado/folga considerada na contagem padrão; amarelo indica data especial.</p></div></div>' + calendar_legend() + '<div class="month-grid">'
    for month in range(1, 13):
        body += f'<section class="month"><h3><a href="calendario-{slugify(MONTHS[month - 1])}-{year}.html">{MONTHS[month - 1].capitalize()} {year}</a></h3>{render_month(year, month)}</section>'
    body += "</div></div></section>"
    write(f"calendario-{year}.html", page(f"Calendário {year} - Brasil", f"Calendário brasileiro {year} com feriados, dias úteis, meses, calendário bancário e datas móveis.", body, f"/calendario-{year}.html", "calendario"))


def generate_month_pages(year: int) -> None:
    for month in range(1, 13):
        month_name = MONTHS[month - 1]
        month_holidays = [item for item in national_holidays(year) if item.date.month == month]
        body = section_hero(
            f"Calendário de {month_name} de {year}",
            f"Veja os dias do mês, fins de semana, feriados nacionais e datas especiais de {month_name} de {year}.",
            actions=f'<a class="btn btn--primary" href="calendario-{year}.html">Calendário {year}</a><a class="btn btn--ghost" href="dias-uteis-{year}.html">Dias úteis</a>',
        )
        body += f'<section class="section"><div class="container"><section class="month month--large"><h2>{month_name.capitalize()} {year}</h2>{calendar_legend()}{render_month(year, month)}</section></div></section>'
        if month_holidays:
            body += f'<section class="section"><div class="container"><h2>Feriados e datas de {month_name} de {year}</h2>{holiday_table(month_holidays)}</div></section>'
        else:
            body += f'<section class="section"><div class="container"><div class="notice">Não há feriado nacional legal neste mês. Confira feriados estaduais e municipais para sua cidade.</div></div></section>'
        write(f"calendario-{slugify(month_name)}-{year}.html", page(f"Calendário de {month_name} de {year}", f"Calendário de {month_name} de {year} no Brasil, com feriados e dias úteis.", body, f"/calendario-{slugify(month_name)}-{year}.html", "calendario"))


def generate_holiday_pages(year: int) -> None:
    items = national_holidays(year)
    body = section_hero(
        f"Feriados {year}",
        f"Lista dos feriados nacionais, datas móveis e datas comuns do calendário brasileiro em {year}, com observações sobre o que é feriado nacional legal, bancário ou local.",
        actions=f'<a class="btn btn--primary" href="calendario-{year}.html">Ver calendário</a><a class="btn btn--ghost" href="feriados-bancarios-{year}.html">Feriados bancários</a>',
    )
    body += f'<section class="section"><div class="container"><h2>Feriados nacionais e datas móveis de {year}</h2>{holiday_table(items)}<p class="notice">Carnaval, Corpus Christi e Sexta-feira Santa têm tratamento específico: podem não ser feriado nacional civil, mas aparecem em calendários bancários, municipais ou religiosos. Para contratos e obrigações locais, confira a legislação da sua cidade.</p></div></section>'
    body += f'<section class="section"><div class="container"><h2>Outros anos</h2>{links_year_nav("feriados", "Feriados")}</div></section>'
    write(f"feriados-{year}.html", page(f"Feriados {year} no Brasil", f"Feriados {year} no Brasil, datas móveis, Carnaval, Páscoa, Corpus Christi e base legal.", body, f"/feriados-{year}.html", "feriados"))


def generate_workday_pages(year: int) -> None:
    rows = []
    for month in range(1, 13):
        days = list(daterange(date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])))
        work = sum(1 for d in days if is_workday(d))
        bank = sum(1 for d in days if is_bank_business_day(d))
        rows.append(f"<tr><td>{MONTHS[month - 1].capitalize()}</td><td>{len(days)}</td><td>{sum(1 for d in days if d.weekday() >= 5)}</td><td>{work}</td><td>{bank}</td></tr>")
    stats = year_stats(year)
    body = section_hero(
        f"Dias úteis {year}",
        f"Veja quantos dias úteis há em {year}, mês a mês, considerando segunda a sexta e feriados nacionais/datas comuns do Brasil.",
        actions='<a class="btn btn--primary" href="calcular-dias-uteis.html">Calcular intervalo</a><a class="btn btn--ghost" href="adicionar-dias-uteis.html">Adicionar dias úteis</a>',
    )
    body += f'<section class="section"><div class="container">{stats_cards(stats)}</div></section>'
    body += '<section class="section"><div class="container"><h2>Dias úteis por mês</h2><div class="table-wrap"><table><thead><tr><th>Mês</th><th>Dias corridos</th><th>Fim de semana</th><th>Dias úteis padrão</th><th>Dias úteis bancários</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table></div></div></section>"
    body += '<section class="section"><div class="container"><div class="notice">A contagem padrão não substitui regras contratuais. Feriados estaduais, municipais, forenses e bancários podem alterar prazos.</div></div></section>'
    write(f"dias-uteis-{year}.html", page(f"Dias úteis {year} - Brasil", f"Quantidade de dias úteis em {year} no Brasil, por mês e no ano.", body, f"/dias-uteis-{year}.html", "dias"))


def generate_banking_pages(year: int) -> None:
    items = banking_holidays(year)
    body = section_hero(
        f"Feriados bancários {year}",
        f"Calendário bancário nacional de {year}, com feriados sem expediente ao público e datas de expediente especial.",
        actions=f'<a class="btn btn--primary" href="calendario-bancario.html">Entender regra bancária</a><a class="btn btn--ghost" href="prazos-{year}.html">Prazos {year}</a>',
    )
    body += f'<section class="section"><div class="container"><h2>Calendário bancário {year}</h2>{holiday_table(items)}<p class="notice">Base metodológica: Resolução CMN nº 4.880/2020, FEBRABAN e ANBIMA. O último dia útil do ano não tem expediente bancário ao público.</p></div></section>'
    write(f"feriados-bancarios-{year}.html", page(f"Feriados bancários {year}", f"Feriados bancários {year} no Brasil e datas com expediente especial.", body, f"/feriados-bancarios-{year}.html", "bancario"))


def generate_deadline_pages(year: int) -> None:
    body = section_hero(
        f"Prazos em {year}",
        f"Guia para contar prazos corridos, dias úteis nacionais e dias úteis bancários em {year}, com links para as calculadoras.",
        actions='<a class="btn btn--primary" href="calcular-dias-uteis.html">Calcular dias úteis</a><a class="btn btn--ghost" href="adicionar-dias-uteis.html">Adicionar prazo</a>',
    )
    body += f"""<section class="section"><div class="container container--narrow prose">
<h2>Como usar este calendário para prazos</h2>
<p>Para boletos, contratos, RH, financeiro e organização interna, a primeira decisão é saber se o prazo é contado em dias corridos, dias úteis comuns ou dias úteis bancários.</p>
<ul>
<li><strong>Dias corridos:</strong> contam todos os dias, inclusive fins de semana e feriados.</li>
<li><strong>Dias úteis padrão:</strong> contam segunda a sexta, excluindo feriados nacionais e datas comuns como Sexta-feira Santa e Corpus Christi.</li>
<li><strong>Dias úteis bancários:</strong> seguem o calendário bancário nacional, incluindo Carnaval, Corpus Christi e o último dia útil do ano sem expediente ao público.</li>
<li><strong>Prazos locais:</strong> podem depender de feriados estaduais, municipais, forenses ou norma específica.</li>
</ul>
<p>Para uso jurídico, tributário, trabalhista ou regulatório, confirme sempre a regra aplicável ao seu caso.</p>
</div></section>"""
    body += f'<section class="section"><div class="container"><h2>Datas bancárias que afetam prazos em {year}</h2>{holiday_table(banking_holidays(year))}</div></section>'
    write(f"prazos-{year}.html", page(f"Prazos {year} - dias úteis, bancários e corridos", f"Como contar prazos em {year}: dias corridos, úteis, bancários e feriados.", body, f"/prazos-{year}.html", "dias"))


def generate_vacation_pages(year: int) -> None:
    rows = []
    for item in build_best_vacation_windows(year):
        rows.append(
            f"<tr><td>{fmt_short(item['start'])}</td><td>{fmt_short(item['end'])}</td><td>{item['days_off']}</td><td>{item['vacation_days']}</td><td>{item['ratio']:.1f}x</td><td>{html.escape(item['holidays'])}</td></tr>"
        )
    body = section_hero(
        f"Melhores dias para tirar folga em {year}",
        f"Sugestões de pontes e emendas para aproveitar feriados nacionais e fins de semana gastando menos dias de férias.",
        actions=f'<a class="btn btn--primary" href="calendario-{year}.html">Calendário {year}</a><a class="btn btn--ghost" href="feriados-{year}.html">Feriados {year}</a>',
    )
    body += '<section class="section"><div class="container"><h2>Melhores janelas de folga</h2><div class="table-wrap"><table><thead><tr><th>Início</th><th>Fim</th><th>Dias de descanso</th><th>Dias úteis usados</th><th>Ganho</th><th>Motivo</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table></div><p class=\"notice\">A sugestão usa calendário nacional padrão. Feriados estaduais, municipais e políticas internas de empresa podem melhorar ou piorar a conta.</p></div></section>"
    write(f"melhores-dias-para-folga-{year}.html", page(f"Melhores dias para tirar folga em {year}", f"Pontes e feriados para tirar folga em {year} usando menos dias de férias.", body, f"/melhores-dias-para-folga-{year}.html", "calendario"))


def generate_movable_pages(year: int) -> None:
    e = easter_sunday(year)
    pages = [
        ("pascoa", "Páscoa", e, [("Carnaval", e - timedelta(days=48)), ("Sexta-feira Santa", e - timedelta(days=2)), ("Páscoa", e), ("Corpus Christi", e + timedelta(days=60))]),
        ("carnaval", "Carnaval", e - timedelta(days=48), [("Segunda de Carnaval", e - timedelta(days=48)), ("Terça de Carnaval", e - timedelta(days=47)), ("Quarta-feira de Cinzas", e - timedelta(days=46))]),
        ("corpus-christi", "Corpus Christi", e + timedelta(days=60), [("Corpus Christi", e + timedelta(days=60))]),
    ]
    for slug, title, main_date, rows_data in pages:
        rows = "".join(f"<tr><td>{name}</td><td>{fmt_short(day)}</td><td>{WEEKDAYS_LONG[day.weekday()]}</td></tr>" for name, day in rows_data)
        body = section_hero(
            f"{title} {year}",
            f"{title} em {year} cai em {fmt_date(main_date)} ({WEEKDAYS_LONG[main_date.weekday()]}).",
            actions=f'<a class="btn btn--primary" href="calendario-{year}.html">Calendário {year}</a><a class="btn btn--ghost" href="feriados-{year}.html">Feriados</a>',
        )
        body += '<section class="section"><div class="container"><h2>Datas relacionadas</h2><div class="table-wrap"><table><thead><tr><th>Data</th><th>Quando</th><th>Dia da semana</th></tr></thead><tbody>' + rows + "</tbody></table></div></div></section>"
        write(f"{slug}-{year}.html", page(f"{title} {year} - data no Brasil", f"Data de {title} em {year} no calendário brasileiro.", body, f"/{slug}-{year}.html", "feriados"))


def generate_state_city_pages(year: int) -> None:
    for state in STATES:
        uf = state["uf"]
        items = holidays_for_scope(year, uf=uf)
        stats = year_stats(year, uf=uf)
        body = section_hero(
            f"Feriados no estado de {state['name']} em {year}",
            f"Feriados nacionais e datas estaduais cadastradas para {state['name']} em {year}.",
            actions=f'<a class="btn btn--primary" href="dias-uteis-{state["slug"]}-{year}.html">Dias úteis no estado</a><a class="btn btn--ghost" href="feriados-estaduais.html">Outros estados</a>',
        )
        body += f'<section class="section"><div class="container">{stats_cards(stats)}</div></section><section class="section"><div class="container"><h2>Lista de feriados</h2>{holiday_table(items)}<p class="notice">Datas estaduais devem ser confirmadas na legislação local quando usadas para folha, contratos e obrigações formais.</p></div></section>'
        write(f"feriados-estado-{state['slug']}-{year}.html", page(f"Feriados {state['name']} {year}", f"Feriados no estado de {state['name']} em {year}, com datas nacionais e estaduais.", body, f"/feriados-estado-{state['slug']}-{year}.html", "locais"))

        rows = []
        for month in range(1, 13):
            days = list(daterange(date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])))
            rows.append(f"<tr><td>{MONTHS[month - 1].capitalize()}</td><td>{sum(1 for d in days if is_workday(d, uf=uf))}</td><td>{sum(1 for d in days if d.weekday() >= 5)}</td></tr>")
        state_days_file = f"dias-uteis-{state['slug']}-{year}.html"
        body = section_hero(
            f"Dias úteis em {state['name']} em {year}",
            f"Contagem mês a mês de dias úteis no estado de {state['name']}, considerando feriados nacionais e datas estaduais cadastradas.",
            actions=f'<a class="btn btn--primary" href="feriados-estado-{state["slug"]}-{year}.html">Feriados no estado</a><a class="btn btn--ghost" href="calcular-dias-uteis.html">Calculadora</a>',
        )
        body += '<section class="section"><div class="container"><div class="table-wrap"><table><thead><tr><th>Mês</th><th>Dias úteis</th><th>Fins de semana</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table></div><p class=\"notice\">A contagem estadual não inclui feriados municipais fora das capitais. Para uso formal, confirme legislação local.</p></div></section>"
        write(state_days_file, page(f"Dias úteis {state['name']} {year}", f"Dias úteis no estado de {state['name']} em {year}, por mês.", body, f"/{state_days_file}", "dias"))

        city_key = f"{state['capital_slug']}-{uf.lower()}"
        city_items = holidays_for_scope(year, uf=uf, city_key=city_key)
        city_stats = year_stats(year, uf=uf, city_key=city_key)
        city_file = f"feriados-{state['capital_slug']}-{uf.lower()}-{year}.html"
        body = section_hero(
            f"Feriados em {state['capital']} - {uf} em {year}",
            f"Feriados nacionais, estaduais e datas municipais cadastradas para {state['capital']} em {year}.",
            actions=f'<a class="btn btn--primary" href="dias-uteis-{state["capital_slug"]}-{uf.lower()}-{year}.html">Dias úteis na cidade</a><a class="btn btn--ghost" href="feriados-capitais.html">Outras capitais</a>',
        )
        body += f'<section class="section"><div class="container">{stats_cards(city_stats)}</div></section><section class="section"><div class="container"><h2>Lista de feriados em {state["capital"]}</h2>{holiday_table(city_items)}<p class="notice">Feriados municipais podem mudar por lei ou decreto. Confirme com a prefeitura para uso formal.</p></div></section>'
        write(city_file, page(f"Feriados {state['capital']} {year}", f"Feriados em {state['capital']} - {uf} em {year}.", body, f"/{city_file}", "locais"))

        rows = []
        for month in range(1, 13):
            days = list(daterange(date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])))
            rows.append(f"<tr><td>{MONTHS[month - 1].capitalize()}</td><td>{sum(1 for d in days if is_workday(d, uf=uf, city_key=city_key))}</td><td>{sum(1 for d in days if d.weekday() >= 5)}</td></tr>")
        file_name = f"dias-uteis-{state['capital_slug']}-{uf.lower()}-{year}.html"
        body = section_hero(
            f"Dias úteis em {state['capital']} - {uf} em {year}",
            f"Contagem mês a mês de dias úteis em {state['capital']} considerando feriados nacionais e datas locais cadastradas.",
            actions=f'<a class="btn btn--primary" href="{city_file}">Feriados na cidade</a><a class="btn btn--ghost" href="calcular-dias-uteis.html">Calculadora</a>',
        )
        body += '<section class="section"><div class="container"><div class="table-wrap"><table><thead><tr><th>Mês</th><th>Dias úteis</th><th>Fins de semana</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table></div><p class=\"notice\">Use esta página como referência prática; feriados locais podem depender de decreto anual.</p></div></section>"
        write(file_name, page(f"Dias úteis {state['capital']} {year}", f"Dias úteis em {state['capital']} - {uf} em {year}, por mês.", body, f"/{file_name}", "dias"))


def generate_static_pages() -> None:
    state_cards = "".join(
        f'<a class="card" href="feriados-estado-{state["slug"]}-{ACTIVE_YEAR}.html"><h3>{state["name"]}</h3><p class="muted">Capital: {state["capital"]}. Ver feriados estaduais e datas locais cadastradas.</p></a>'
        for state in STATES
    )
    body = section_hero("Feriados estaduais", "Páginas por estado com feriados nacionais e datas estaduais cadastradas.", actions=f'<a class="btn btn--primary" href="feriados-capitais.html">Ver capitais</a>')
    body += f'<section class="section"><div class="container"><div class="grid">{state_cards}</div></div></section>'
    write("feriados-estaduais.html", page("Feriados estaduais do Brasil", "Feriados por estado brasileiro, com datas nacionais e estaduais cadastradas.", body, "/feriados-estaduais.html", "locais"))

    city_cards = "".join(
        f'<a class="card" href="feriados-{state["capital_slug"]}-{state["uf"].lower()}-{ACTIVE_YEAR}.html"><h3>{state["capital"]} - {state["uf"]}</h3><p class="muted">Feriados e dias úteis na capital.</p></a>'
        for state in STATES
    )
    body = section_hero("Feriados nas capitais", "Páginas por capital com feriados nacionais, estaduais e datas municipais cadastradas.", actions='<a class="btn btn--primary" href="feriados-estaduais.html">Ver estados</a>')
    body += f'<section class="section"><div class="container"><div class="grid">{city_cards}</div></div></section>'
    write("feriados-capitais.html", page("Feriados nas capitais brasileiras", "Feriados nas capitais brasileiras, com datas nacionais e locais.", body, "/feriados-capitais.html", "locais"))

    tool_intro = section_hero("Calculadora de dias úteis", "Calcule dias úteis entre duas datas usando calendário nacional padrão ou calendário bancário.", actions='<a class="btn btn--ghost" href="adicionar-dias-uteis.html">Adicionar dias úteis</a>')
    tool = """<section class="section"><div class="container"><div class="tool" data-tool="diff">
<div class="tool-grid"><div class="field"><label for="diff-start">Data inicial</label><input id="diff-start" type="date"></div><div class="field"><label for="diff-end">Data final</label><input id="diff-end" type="date"></div><div class="field"><label for="diff-mode">Calendário</label><select id="diff-mode"><option value="standard">Dias úteis nacionais</option><option value="bank">Dias úteis bancários</option><option value="corridos">Dias corridos</option></select></div><div class="field"><label for="diff-inclusive">Incluir data inicial?</label><select id="diff-inclusive"><option value="no">Não</option><option value="yes">Sim</option></select></div></div>
<button class="btn btn--primary" id="diff-run" type="button">Calcular</button><div class="result-box" id="diff-result" hidden></div></div></div></section>"""
    write("calcular-dias-uteis.html", page("Calculadora de dias úteis", "Calcule dias úteis entre duas datas no Brasil, com modo nacional e bancário.", tool_intro + tool, "/calcular-dias-uteis.html", "calc"))

    body = section_hero("Adicionar dias úteis", "Some dias úteis a uma data inicial e encontre a data final, com calendário nacional ou bancário.", actions='<a class="btn btn--ghost" href="calcular-dias-uteis.html">Calcular intervalo</a>')
    body += """<section class="section"><div class="container"><div class="tool" data-tool="add">
<div class="tool-grid"><div class="field"><label for="add-start">Data inicial</label><input id="add-start" type="date"></div><div class="field"><label for="add-days">Quantidade de dias úteis</label><input id="add-days" type="number" min="0" value="5"></div><div class="field"><label for="add-mode">Calendário</label><select id="add-mode"><option value="standard">Dias úteis nacionais</option><option value="bank">Dias úteis bancários</option></select></div></div>
<button class="btn btn--primary" id="add-run" type="button">Adicionar</button><div class="result-box" id="add-result" hidden></div></div></div></section>"""
    write("adicionar-dias-uteis.html", page("Adicionar dias úteis", "Adicione dias úteis a uma data no Brasil e encontre a data final.", body, "/adicionar-dias-uteis.html", "calc"))

    body = section_hero("Número da semana", "Descubra a semana ISO de qualquer data e o dia da semana correspondente.", actions='<a class="btn btn--ghost" href="calendario-2026.html">Ver calendário</a>')
    body += """<section class="section"><div class="container"><div class="tool" data-tool="week"><div class="tool-grid"><div class="field"><label for="week-date">Data</label><input id="week-date" type="date"></div></div><button class="btn btn--primary" id="week-run" type="button">Ver semana</button><div class="result-box" id="week-result" hidden></div></div></div></section>"""
    write("numero-da-semana.html", page("Número da semana", "Encontre o número da semana ISO para uma data.", body, "/numero-da-semana.html", "calc"))

    body = section_hero("Calendário bancário", "Consulte feriados bancários nacionais, dias úteis bancários e datas com expediente especial.", actions=f'<a class="btn btn--primary" href="feriados-bancarios-{ACTIVE_YEAR}.html">Feriados bancários {ACTIVE_YEAR}</a>')
    body += f'<section class="section"><div class="container"><h2>Anos disponíveis</h2>{links_year_nav("feriados-bancarios", "Bancário")}</div></section>'
    write("calendario-bancario.html", page("Calendário bancário do Brasil", "Calendário bancário brasileiro com feriados e dias úteis bancários.", body, "/calendario-bancario.html", "bancario"))

    body = section_hero("Sobre", "O Calendário Brasileiro organiza feriados, dias úteis, datas bancárias e páginas locais para planejamento prático.", actions='<a class="btn btn--primary" href="fontes.html">Ver fontes</a>')
    body += """<section class="section"><div class="container container--narrow prose"><h2>Como trabalhamos</h2><p>O site é estático, gerado por script e revisado por fontes públicas. Datas nacionais fixas vêm de leis federais; datas móveis usam cálculo da Páscoa gregoriana; calendário bancário segue regras do mercado financeiro; datas estaduais e municipais são um cadastro prático para consulta inicial.</p><p>Não substituímos consulta jurídica, legislação municipal, normas internas de empresa ou calendários oficiais de tribunais.</p></div></section>"""
    write("sobre.html", page("Sobre o Calendário Brasileiro", "Sobre o Calendário Brasileiro e a metodologia do site.", body, "/sobre.html"))

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
    rows = "".join(f'<tr><td><a href="{url}" rel="noopener">{name}</a></td><td>{desc}</td></tr>' for name, url, desc in sources)
    body = section_hero("Fontes e metodologia", "Fontes públicas usadas para montar os calendários nacionais, bancários e locais.", actions='<a class="btn btn--primary" href="contato.html">Reportar correção</a>')
    body += '<section class="section"><div class="container"><div class="table-wrap"><table><thead><tr><th>Fonte</th><th>Uso</th></tr></thead><tbody>' + rows + "</tbody></table></div></div></section>"
    write("fontes.html", page("Fontes e metodologia", "Fontes oficiais e metodologia do Calendário Brasileiro.", body, "/fontes.html"))

    body = section_hero("Contato", "Encontrou uma data local incorreta ou quer sugerir melhoria? Fale com a gente.", actions=f'<a class="btn btn--primary" href="mailto:{CONTACT_EMAIL}">Enviar e-mail</a>')
    body += f'<section class="section"><div class="container container--narrow prose"><p>E-mail: <a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a></p><p>Ao reportar uma correção, envie o link da fonte oficial estadual, municipal, bancária ou normativa.</p></div></section>'
    write("contato.html", page("Contato", "Contato do Calendário Brasileiro.", body, "/contato.html"))

    body = section_hero("Privacidade", "Esta política explica cookies, anúncios e dados de navegação.", actions="")
    body += """<section class="section"><div class="container container--narrow prose"><h2>Cookies e anúncios</h2><p>Podemos usar cookies e tecnologias similares para funcionamento do site, métricas agregadas e anúncios. O Google AdSense pode usar cookies para personalizar ou medir anúncios conforme as políticas do Google.</p><h2>Dados pessoais</h2><p>As calculadoras rodam no navegador e não exigem cadastro. Se você enviar e-mail, usaremos as informações apenas para responder.</p><h2>Seus direitos</h2><p>Você pode solicitar informações ou remoção de dados de contato pelo e-mail informado na página de contato.</p></div></section>"""
    write("privacidade.html", page("Política de privacidade", "Política de privacidade do Calendário Brasileiro.", body, "/privacidade.html"))

    body = section_hero("Termos de uso", "Condições de uso das ferramentas e calendários.", actions="")
    body += """<section class="section"><div class="container container--narrow prose"><h2>Uso informativo</h2><p>O conteúdo é informativo e pode conter simplificações. Para decisões jurídicas, trabalhistas, fiscais, financeiras ou regulatórias, consulte a fonte oficial e profissionais qualificados.</p><h2>Feriados locais</h2><p>Estados e municípios podem alterar datas por lei ou decreto. Páginas locais são referência inicial, não certidão oficial.</p><h2>Disponibilidade</h2><p>O site pode ser atualizado, corrigido ou ficar indisponível temporariamente.</p></div></section>"""
    write("termos.html", page("Termos de uso", "Termos de uso e aviso de responsabilidade.", body, "/termos.html"))

    body = section_hero("Apoie o projeto", "Se o calendário economizou seu tempo, você pode apoiar a manutenção.", actions=f'<a class="btn btn--primary" href="{BUY_ME_A_COFFEE}" rel="noopener">Buy me a coffee</a>')
    body += '<section class="section"><div class="container container--narrow"><article class="card donate-card"><h2>Obrigado pelo apoio</h2><p class="muted">A contribuição ajuda a manter as páginas estáticas, revisar fontes e acrescentar novas cidades.</p><a class="btn btn--primary" href="' + BUY_ME_A_COFFEE + '" rel="noopener">Apoiar no Buy Me a Coffee</a></article></div></section>'
    write("apoiar.html", page("Apoie o Calendário Brasileiro", "Apoie a manutenção do Calendário Brasileiro.", body, "/apoiar.html"))

    body = section_hero("Página não encontrada", "A página que você tentou acessar não existe ou mudou de endereço.", actions='<a class="btn btn--primary" href="index.html">Voltar ao início</a>')
    write("404.html", page("Página não encontrada - 404", "Página não encontrada no Calendário Brasileiro.", body, "/404.html"))


def write_assets() -> None:
    css = r""":root{--bg:#f6f7f2;--paper:#fff;--ink:#18211b;--muted:#687268;--line:#dfe5dc;--brand:#166534;--brand2:#0f766e;--accent:#b45309;--soft:#ecfdf5;--danger:#b91c1c;--radius:8px;--shadow:0 12px 28px rgba(15,23,42,.08)}
*{box-sizing:border-box}html{font-family:Inter,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:var(--ink);background:var(--bg);line-height:1.55}body{margin:0}a{color:#0f766e}a:hover{color:#0b5d55}.skip-link{position:absolute;left:-999px}.skip-link:focus{left:1rem;top:1rem;background:#fff;padding:.6rem 1rem;border:2px solid var(--brand);z-index:99}.container{width:min(1140px,calc(100% - 32px));margin-inline:auto}.container--narrow{width:min(820px,calc(100% - 32px));margin-inline:auto}.site-header{background:#fff;border-bottom:1px solid var(--line);position:sticky;top:0;z-index:20}.site-header__inner{display:flex;align-items:center;gap:1rem;justify-content:space-between;min-height:64px}.brand{display:flex;align-items:center;gap:.65rem;text-decoration:none;color:var(--ink);font-weight:850}.brand__mark{width:36px;height:36px}.brand--footer{color:#fff}.main-nav ul{list-style:none;margin:0;padding:0;display:flex;gap:.25rem;flex-wrap:wrap}.main-nav a{display:block;text-decoration:none;color:var(--muted);padding:.55rem .7rem;border-radius:6px;font-weight:700;font-size:.95rem}.main-nav a[aria-current=page],.main-nav a:hover{background:#eef7f0;color:#14532d}.hero{padding:2.8rem 0 1.8rem;background:linear-gradient(180deg,#fff 0,#f6f7f2 100%)}.hero-grid{display:grid;grid-template-columns:minmax(0,1.05fr) minmax(280px,.95fr);gap:2rem;align-items:start}.eyebrow{font-size:.8rem;text-transform:uppercase;letter-spacing:.08em;color:var(--brand);font-weight:850}.hero h1{font-size:clamp(2rem,5vw,4.25rem);line-height:1.02;margin:.35rem 0 1rem;letter-spacing:0}.lead{font-size:1.12rem;color:#3b473e;max-width:70ch}.hero-actions{display:flex;gap:.7rem;flex-wrap:wrap;margin-top:1.3rem}.btn{display:inline-flex;align-items:center;justify-content:center;text-decoration:none;border-radius:7px;padding:.72rem 1rem;font-weight:850;border:1px solid transparent;cursor:pointer;font:inherit}.btn--primary{background:var(--brand);color:#fff}.btn--primary:hover{background:#14532d;color:#fff}.btn--ghost{border-color:var(--line);background:#fff;color:var(--ink)}.quick-panel{background:#fff;border:1px solid var(--line);border-radius:var(--radius);box-shadow:var(--shadow);padding:1rem}.mini-calendar{display:grid;grid-template-columns:repeat(7,1fr);gap:4px}.mini-calendar span{display:flex;align-items:center;justify-content:center;min-height:34px;border-radius:5px;background:#f4f6f2;font-size:.85rem}.mini-calendar .head{background:#e6ece6;color:#475047;font-weight:850}.mini-calendar .holiday{background:#fee2e2;color:#991b1b;font-weight:850}.mini-calendar .special{background:#fef3c7;color:#92400e}.mini-calendar .today{outline:2px solid var(--brand);background:#ecfdf5}.section{padding:2rem 0}.section-title{display:flex;align-items:end;justify-content:space-between;gap:1rem;margin-bottom:1rem}.section-title h2{margin:0;font-size:1.55rem}.section-title p{margin:.2rem 0 0;color:var(--muted)}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(235px,1fr));gap:1rem}.card{background:#fff;border:1px solid var(--line);border-radius:var(--radius);padding:1rem;box-shadow:0 8px 18px rgba(15,23,42,.04)}a.card{text-decoration:none;color:inherit}a.card:hover{border-color:#86efac;box-shadow:var(--shadow)}.card h3{margin:.1rem 0 .4rem}.stat{font-size:2rem;font-weight:900;color:#166534;margin:.2rem 0}.muted{color:var(--muted)}.muted-on-dark{color:#b8c6bd}.prose{font-size:1.03rem}.prose h2{margin-top:1.8rem}.prose p,.prose li{color:#33403a}.prose li{margin:.35rem 0}.table-wrap{overflow-x:auto;background:#fff;border:1px solid var(--line);border-radius:var(--radius)}table{border-collapse:collapse;width:100%;min-width:700px}th,td{padding:.72rem .8rem;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}th{background:#eef2ee;color:#475047;font-size:.82rem;text-transform:uppercase;letter-spacing:.04em}.month-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(285px,1fr));gap:1rem}.month{background:#fff;border:1px solid var(--line);border-radius:var(--radius);padding:.8rem}.month--large{max-width:760px;margin:auto}.month h3{margin:0 0 .65rem;text-transform:capitalize}.calendar-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:3px}.calendar-grid span{min-height:32px;display:flex;align-items:center;justify-content:center;border-radius:5px;background:#f8faf7;font-size:.86rem}.month--large .calendar-grid span{min-height:54px}.calendar-grid .head{font-weight:850;background:#e7ece7;color:#4b554d}.calendar-grid .empty{background:transparent}.calendar-grid .weekend{background:#f1f5f9;color:#64748b}.calendar-grid .holiday{background:#fee2e2;color:#991b1b;font-weight:850}.calendar-grid .special{background:#fef3c7;color:#92400e}.calendar-grid .today{outline:2px solid var(--brand)}.tool{background:#fff;border:1px solid var(--line);border-radius:var(--radius);padding:1rem;box-shadow:var(--shadow)}.tool-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:.8rem;margin-bottom:1rem}.field label{display:block;font-weight:800;margin-bottom:.25rem}.field input,.field select{width:100%;padding:.68rem .75rem;border:1px solid #cbd5cf;border-radius:6px;font:inherit}.result-box{margin-top:1rem;background:#ecfdf5;border:1px solid #bbf7d0;border-radius:7px;padding:1rem}.notice{background:#fffbeb;border:1px solid #fde68a;border-radius:7px;padding:1rem;color:#713f12}.donate-card{text-align:center}.footer{margin-top:2rem;padding:2rem 0;background:#10201c;color:#e7f5ef}.footer a{color:#a7f3d0}.footer-grid{display:grid;grid-template-columns:2fr repeat(3,1fr);gap:1rem}.footer ul{list-style:none;padding:0;margin:.4rem 0}.footer li{margin:.25rem 0}.tag-cloud{display:flex;flex-wrap:wrap;gap:.45rem}.tag-link{display:inline-flex;text-decoration:none;padding:.35rem .62rem;border-radius:999px;background:#fff;border:1px solid var(--line);font-weight:800;color:#14532d}.tag{display:inline-flex;padding:.18rem .45rem;border-radius:999px;background:#eef7f4;color:#0f5f59;font-size:.78rem;font-weight:850}@media(max-width:780px){.hero-grid{grid-template-columns:1fr}.footer-grid{grid-template-columns:1fr}.section-title{display:block}table{min-width:620px}.main-nav a{font-size:.86rem;padding:.45rem}.month--large .calendar-grid span{min-height:42px}}
.calendar-legend{display:flex;flex-wrap:wrap;gap:.55rem .85rem;align-items:center;margin:0 0 1rem;padding:.75rem .85rem;background:#fff;border:1px solid var(--line);border-radius:var(--radius)}.month--large .calendar-legend{margin-top:.35rem}.calendar-legend__item{display:inline-flex;align-items:center;gap:.4rem;color:#475047;font-size:.9rem;font-weight:700}.calendar-legend__swatch{width:18px;height:18px;border-radius:5px;border:1px solid var(--line);display:inline-block}.calendar-legend__swatch--holiday{background:#fee2e2;border-color:#fecaca}.calendar-legend__swatch--special{background:#fef3c7;border-color:#fde68a}.calendar-legend__swatch--weekend{background:#f1f5f9;border-color:#e2e8f0}.calendar-legend__swatch--today{background:#ecfdf5;border-color:var(--brand);outline:2px solid var(--brand);outline-offset:0}
"""
    write("css/style.css", css)
    js = r"""(function(){
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
    $('diff-start').value = isoDate(today);
    $('diff-end').value = isoDate(addDays(today, 30));
    $('diff-run').addEventListener('click', () => {
      const start = parse($('diff-start').value), end = parse($('diff-end').value);
      const mode = $('diff-mode').value;
      const count = countUseful(start, end, mode, $('diff-inclusive').value === 'yes');
      const box = $('diff-result');
      box.hidden = false;
      box.innerHTML = count === null ? 'Informe as duas datas.' : `<strong>${count}</strong> dia(s) ${mode === 'corridos' ? 'corrido(s)' : 'útil(eis)'} no intervalo.`;
    });
  }
  function bootAdd(){
    if (!$('add-run')) return;
    const today = new Date();
    $('add-start').value = isoDate(today);
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
    $('week-date').value = isoDate(today);
    $('week-run').addEventListener('click', () => {
      const d = parse($('week-date').value);
      const box = $('week-result');
      box.hidden = false;
      if (!d) { box.textContent = 'Informe uma data.'; return; }
      box.innerHTML = `${fmt(d)} cai em <strong>${['domingo','segunda-feira','terça-feira','quarta-feira','quinta-feira','sexta-feira','sábado'][d.getUTCDay()]}</strong> e está na semana ISO <strong>${isoWeek(d)}</strong>.`;
    });
  }
  document.addEventListener('DOMContentLoaded', () => { bootDiff(); bootAdd(); bootWeek(); });
})();"""
    write("js/calendar-tools.js", js)
    write("favicon.svg", brand_svg().replace('class="brand__mark" ', "").replace("aria-hidden=\"true\"", "xmlns=\"http://www.w3.org/2000/svg\""))
    write("CNAME", "calendariobrasileiro.com.br\n")
    write("ads.txt", "google.com, pub-7516029395999799, DIRECT, f08c47fec0942fa0\n")
    write("robots.txt", "User-agent: *\nAllow: /\nSitemap: https://calendariobrasileiro.com.br/sitemap.xml\n")
    manifest = {
        "name": "Calendário Brasileiro",
        "short_name": "Calendário BR",
        "description": "Calendário brasileiro com feriados, dias úteis e prazos.",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#166534",
        "lang": "pt-BR",
        "icons": [{"src": "/favicon.svg", "sizes": "64x64", "type": "image/svg+xml"}],
    }
    write("site.webmanifest", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")


def generate_data() -> None:
    payload = {"generatedAt": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"), "startYear": START_YEAR, "endYear": END_YEAR, "years": {}}
    for year in range(START_YEAR, END_YEAR + 1):
        payload["years"][str(year)] = {
            "holidays": [
                {"date": item.date.isoformat(), "name": item.name, "kind": item.kind, "scope": item.scope, "official": item.official}
                for item in national_holidays(year)
            ],
            "standardExcluded": sorted(d.isoformat() for d in standard_nonwork_dates(year)),
            "bankExcluded": sorted(item.date.isoformat() for item in banking_holidays(year) if item.kind != "expediente bancário especial"),
        }
    write("data/calendarios.json", json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    write("js/calendar-data.js", "window.CB_CALENDAR_DATA = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n")


def generate_sitemap(html_files: list[str]) -> None:
    urls = []
    for name in sorted(html_files):
        if name == "404.html":
            continue
        loc = DOMAIN + "/" if name == "index.html" else f"{DOMAIN}/{name}"
        urls.append(f"  <url><loc>{loc}</loc><lastmod>{date.today().isoformat()}</lastmod></url>")
    content = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(urls) + "\n</urlset>\n"
    write("sitemap.xml", content)


def clean_generated() -> None:
    for pattern in ("*.html",):
        for path in ROOT.glob(pattern):
            path.unlink()
    for folder in ("css", "js", "data"):
        (ROOT / folder).mkdir(exist_ok=True)


def generate_all() -> None:
    clean_generated()
    write_assets()
    generate_data()
    generate_index()
    for year in range(START_YEAR, END_YEAR + 1):
        generate_year_pages(year)
        generate_month_pages(year)
        generate_holiday_pages(year)
        generate_workday_pages(year)
        generate_banking_pages(year)
        generate_deadline_pages(year)
        generate_vacation_pages(year)
        generate_movable_pages(year)
        generate_state_city_pages(year)
    generate_static_pages()
    html_files = [path.name for path in ROOT.glob("*.html")]
    generate_sitemap(html_files)
    annual_review = """# Revisão anual do Calendário Brasileiro

Rodar preferencialmente em novembro/dezembro:

1. Conferir se houve mudança em leis federais de feriados nacionais.
2. Conferir calendário bancário FEBRABAN/ANBIMA para o ano seguinte.
3. Conferir decretos estaduais e municipais das capitais cadastradas.
4. Conferir calendário eleitoral no TSE em anos pares.
5. Rodar `python tools/generate_site.py` e `python tools/validate_site.py`.
6. Publicar e reenviar sitemap no Search Console.
"""
    write("README.md", annual_review)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=START_YEAR)
    parser.add_argument("--end", type=int, default=END_YEAR)
    args = parser.parse_args()
    if args.start != START_YEAR or args.end != END_YEAR:
        raise SystemExit("Edite START_YEAR/END_YEAR no script para mudar o intervalo e manter o build reprodutível.")
    generate_all()
    print(f"Generated Calendario Brasileiro: {len(list(ROOT.glob('*.html')))} HTML files")


if __name__ == "__main__":
    main()
