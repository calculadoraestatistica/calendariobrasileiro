#!/usr/bin/env python3
"""Render the 8 extra date-utility tool pages for Calendario Brasileiro.

These pages reuse the shared ``layout`` function exported by
``generate_site.py`` so the header, footer, ad slots, breadcrumb JSON-LD and
FAQPage JSON-LD stay consistent with the rest of the site. Every page is a
self-contained calculator with inline JavaScript that works in the browser
without external dependencies.
"""

from __future__ import annotations

import html
import json
from datetime import date
from pathlib import Path
from typing import Callable, Iterable


# -- shared bits ------------------------------------------------------------

RELATED_TOOLS = [
    ("calcular-dias-uteis.html", "Calcular dias úteis",
     "Conte dias úteis entre duas datas no Brasil."),
    ("adicionar-dias-uteis.html", "Adicionar dias úteis",
     "Some N dias úteis a uma data inicial."),
    ("subtrair-dias-uteis.html", "Subtrair dias úteis",
     "Recue N dias úteis a partir de uma data."),
    ("numero-da-semana.html", "Número da semana",
     "Descubra a semana ISO de qualquer data."),
    ("data-da-semana.html", "Data da semana ISO",
     "Dado ano + semana + dia, descubra a data."),
    ("calculadora-idade.html", "Calculadora de idade",
     "Idade exata em anos, meses e dias."),
    ("diferenca-entre-datas.html", "Diferença entre datas",
     "Anos, meses, semanas, dias, horas e minutos."),
    ("countdown.html", "Contagem regressiva",
     "Tempo restante até uma data, ao vivo."),
    ("proximo-feriado.html", "Próximo feriado",
     "Próximos feriados nacionais brasileiros."),
    ("dia-da-semana.html", "Dia da semana",
     "Em qual dia da semana caiu/cai uma data."),
    ("data-mais-dias.html", "Data ± N dias",
     "Some ou subtraia N dias corridos."),
]


def _related_grid(exclude_slug: str) -> str:
    cards = []
    for href, title, desc in RELATED_TOOLS:
        if href == exclude_slug:
            continue
        cards.append(
            f'<a class="card" href="{html.escape(href)}">'
            f'<h3>{html.escape(title)}</h3>'
            f'<p class="muted">{html.escape(desc)}</p></a>'
        )
        if len(cards) >= 6:
            break
    return (
        '<section class="section"><div class="container">'
        '<div class="section-title"><div><h2>Outras ferramentas</h2>'
        '<p>Continue explorando as calculadoras de data.</p></div></div>'
        '<div class="grid">' + "".join(cards) + "</div></div></section>"
    )


def _hero(layout_fn, title: str, lead: str, primary_href: str, primary_label: str,
          ghost_href: str = "calcular-dias-uteis.html",
          ghost_label: str = "Calcular dias úteis") -> str:
    """Build hero using the helpers exposed by the generator module."""
    import generate_site as gs  # local import to avoid cycle at import time
    actions = (
        f'<a class="btn btn--primary" href="{html.escape(primary_href)}">'
        f'{html.escape(primary_label)}</a>'
        f'<a class="btn btn--ghost" href="{html.escape(ghost_href)}">'
        f'{html.escape(ghost_label)}</a>'
    )
    return gs.hero(title, lead, actions=actions)


def _ad(position: str) -> str:
    import generate_site as gs
    return gs.ad_slot(position)


def _write(out_dir: Path, layout_fn, slug: str, title: str, description: str,
           body: str, breadcrumbs, faq) -> None:
    page_html = layout_fn(title, description, slug, body, "calc", breadcrumbs, faq)
    (out_dir / slug).write_text(page_html, encoding="utf-8")


# -- calculadora-idade.html -------------------------------------------------

def render_calculadora_idade(out_dir: Path, layout_fn, **deps) -> None:
    today_iso = date.today().isoformat()
    slug = "calculadora-idade.html"
    title = "Calculadora de Idade - anos, meses e dias"
    description = (
        "Calculadora de idade exata em anos, meses e dias. Veja também total de "
        "dias vividos, semanas, horas e quantos dias faltam para o próximo aniversário."
    )

    body = _hero(
        layout_fn,
        "Calculadora de Idade",
        "Descubra sua idade exata em anos, meses e dias, total de dias vividos, "
        "semanas, horas e quantos dias faltam para o próximo aniversário.",
        primary_href="diferenca-entre-datas.html",
        primary_label="Diferença entre datas",
    )
    body += _ad("header")
    body += f"""<section class="section"><div class="container"><div class="tool" data-tool="idade">
<div class="tool-grid">
<div class="field"><label for="idade-nasc">Data de nascimento</label><input id="idade-nasc" type="date" required></div>
<div class="field"><label for="idade-ref">Data de referência</label><input id="idade-ref" type="date" value="{today_iso}"></div>
</div>
<button class="btn btn--primary" id="idade-run" type="button">Calcular idade</button>
<div class="result-box" id="idade-result" hidden aria-live="polite" aria-atomic="true"></div>
</div></div></section>
<script>
(function(){{
  var WEEKDAYS_LONG=['domingo','segunda-feira','terça-feira','quarta-feira','quinta-feira','sexta-feira','sábado'];
  function parseUTC(s){{var p=(s||'').split('-').map(Number);if(p.length!==3)return null;return new Date(Date.UTC(p[0],p[1]-1,p[2]));}}
  function daysInMonth(y,m){{return new Date(Date.UTC(y,m+1,0)).getUTCDate();}}
  function fmt(d){{return d.toLocaleDateString('pt-BR',{{timeZone:'UTC'}});}}
  function calc(){{
    var birth=parseUTC(document.getElementById('idade-nasc').value);
    var ref=parseUTC(document.getElementById('idade-ref').value);
    var box=document.getElementById('idade-result');
    box.hidden=false;
    if(!birth){{box.textContent='Informe a data de nascimento.';return;}}
    if(!ref){{ref=new Date(Date.UTC(new Date().getUTCFullYear(),new Date().getUTCMonth(),new Date().getUTCDate()));}}
    if(ref<birth){{box.textContent='A data de referência precisa ser igual ou posterior ao nascimento.';return;}}
    var by=birth.getUTCFullYear(),bm=birth.getUTCMonth(),bd=birth.getUTCDate();
    var ry=ref.getUTCFullYear(),rm=ref.getUTCMonth(),rd=ref.getUTCDate();
    var years=ry-by,months=rm-bm,days=rd-bd;
    if(days<0){{months-=1;days+=daysInMonth(by,bm);}}
    if(months<0){{years-=1;months+=12;}}
    var totalDays=Math.floor((ref-birth)/86400000);
    var weeks=Math.floor(totalDays/7);
    var hours=totalDays*24;
    var nextY=ry;
    var next=new Date(Date.UTC(nextY,bm,bd));
    if(next<=ref){{next=new Date(Date.UTC(nextY+1,bm,bd));}}
    var daysToNext=Math.ceil((next-ref)/86400000);
    var weekday=WEEKDAYS_LONG[birth.getUTCDay()];
    box.innerHTML=
      '<p><strong>'+years+'</strong> ano(s), <strong>'+months+'</strong> mês(es) e <strong>'+days+'</strong> dia(s).</p>'+
      '<p>Total: <strong>'+totalDays.toLocaleString('pt-BR')+'</strong> dias · '+
      '<strong>'+weeks.toLocaleString('pt-BR')+'</strong> semanas · '+
      '<strong>'+hours.toLocaleString('pt-BR')+'</strong> horas.</p>'+
      '<p>Próximo aniversário: <strong>'+fmt(next)+'</strong> (faltam '+daysToNext+' dia(s)).</p>'+
      '<p>Você nasceu em uma <strong>'+weekday+'</strong>.</p>';
  }}
  document.addEventListener('DOMContentLoaded',function(){{
    document.getElementById('idade-run').addEventListener('click',calc);
  }});
}})();
</script>"""
    body += _ad("mid")
    body += """<section class="section"><div class="container container--narrow prose">
<h2>Para que serve</h2>
<p>A calculadora de idade entrega a duração entre a data de nascimento e a data de referência em anos, meses e dias. É útil para contratos, formulários, escola, certidões, idade gestacional, faixa etária em planos de saúde e curiosidade pessoal.</p>
<h2>Como calculamos</h2>
<p>Subtraímos o ano, o mês e o dia de nascimento da data de referência e fazemos os ajustes quando o dia ou o mês ficam negativos. O total de dias usa a diferença direta em milissegundos (em UTC, para evitar erro de fuso). Semanas são o total de dias dividido por 7. Horas são total de dias vezes 24.</p>
<h2>Exemplo</h2>
<p>Quem nasceu em 1990-05-12 e consulta em 2026-06-11 tem 36 anos, 0 meses e 30 dias. Total de 13.179 dias. O próximo aniversário é 12 de maio de 2027.</p>
</div></section>"""
    body += _related_grid(slug)

    faq = [
        ("Como a idade exata é calculada?",
         "Usamos a regra civil brasileira: completa-se um ano sempre que a data atual passa pelo dia e mês do aniversário. Antes disso, o ano corrente ainda não foi cumprido."),
        ("Posso usar uma data de referência diferente de hoje?",
         "Sim. Por padrão usamos a data de hoje, mas você pode informar qualquer data para saber a idade em um momento específico."),
        ("Por que o total de dias é diferente de anos × 365?",
         "Cada ano tem 365 ou 366 dias por causa dos anos bissextos. Por isso preferimos calcular a diferença direta em dias corridos."),
        ("Funciona para qualquer ano?",
         "Sim. A calculadora aceita datas de nascimento de qualquer ano e calcula corretamente sobre o calendário gregoriano."),
        ("O cálculo conta o dia do aniversário?",
         "Sim. Se hoje é o seu aniversário, a calculadora já mostra o ano novo completo."),
        ("Por que mostram horas vividas?",
         "É um número alto e curioso, útil para visualizar a quantidade de tempo. Multiplicamos o total de dias por 24."),
    ]
    breadcrumbs = [("Início", "index.html"), ("Calculadora de idade", "")]
    _write(out_dir, layout_fn, slug, title, description, body, breadcrumbs, faq)


# -- diferenca-entre-datas.html ---------------------------------------------

def render_diferenca_entre_datas(out_dir: Path, layout_fn, **deps) -> None:
    today_iso = date.today().isoformat()
    slug = "diferenca-entre-datas.html"
    title = "Diferença entre Datas - anos, meses, semanas e dias"
    description = (
        "Calcule a diferença entre duas datas em anos, meses, semanas, dias, "
        "horas e minutos. Útil para gestação, contratos e projetos."
    )

    body = _hero(
        layout_fn,
        "Diferença entre Datas",
        "Diferença entre duas datas em anos, meses, semanas, dias, horas e minutos. "
        "Ideal para gestação, contratos, projetos e prazos pessoais.",
        primary_href="calcular-dias-uteis.html",
        primary_label="Calcular dias úteis",
        ghost_href="calculadora-idade.html",
        ghost_label="Calculadora de idade",
    )
    body += _ad("header")
    body += f"""<section class="section"><div class="container"><div class="tool" data-tool="diff2">
<div class="tool-grid">
<div class="field"><label for="d2-a">Data 1</label><input id="d2-a" type="date" value="{today_iso}"></div>
<div class="field"><label for="d2-b">Data 2</label><input id="d2-b" type="date"></div>
<div class="field"><label for="d2-inc">Incluir a data final?</label><select id="d2-inc"><option value="no">Não</option><option value="yes">Sim</option></select></div>
</div>
<button class="btn btn--primary" id="d2-run" type="button">Calcular diferença</button>
<div class="result-box" id="d2-result" hidden aria-live="polite" aria-atomic="true"></div>
</div></div></section>
<script>
(function(){{
  function parseUTC(s){{var p=(s||'').split('-').map(Number);if(p.length!==3)return null;return new Date(Date.UTC(p[0],p[1]-1,p[2]));}}
  function daysInMonth(y,m){{return new Date(Date.UTC(y,m+1,0)).getUTCDate();}}
  function relDelta(a,b){{
    var sign=a<=b?1:-1;
    var s=sign>0?a:b,e=sign>0?b:a;
    var y=e.getUTCFullYear()-s.getUTCFullYear();
    var m=e.getUTCMonth()-s.getUTCMonth();
    var d=e.getUTCDate()-s.getUTCDate();
    if(d<0){{m-=1;d+=daysInMonth(s.getUTCFullYear(),s.getUTCMonth());}}
    if(m<0){{y-=1;m+=12;}}
    return {{years:y*sign,months:m*sign,days:d*sign}};
  }}
  function calc(){{
    var a=parseUTC(document.getElementById('d2-a').value);
    var b=parseUTC(document.getElementById('d2-b').value);
    var inc=document.getElementById('d2-inc').value==='yes';
    var box=document.getElementById('d2-result');
    box.hidden=false;
    if(!a||!b){{box.textContent='Informe as duas datas.';return;}}
    var rd=relDelta(a,b);
    var ms=b-a;
    if(inc){{ms+=86400000*(b>=a?1:-1);}}
    var totalDays=Math.round(ms/86400000);
    var absDays=Math.abs(totalDays);
    var sign=totalDays<0?'-':'';
    var weeks=Math.floor(absDays/7);
    var remDays=absDays%7;
    var hours=absDays*24;
    var minutes=absDays*1440;
    var seconds=absDays*86400;
    box.innerHTML=
      '<p>Diferença em calendário: <strong>'+rd.years+'</strong> ano(s), <strong>'+rd.months+'</strong> mês(es), <strong>'+rd.days+'</strong> dia(s).</p>'+
      '<p>Total: <strong>'+sign+absDays.toLocaleString('pt-BR')+'</strong> dias corridos ('+sign+weeks.toLocaleString('pt-BR')+' semanas e '+remDays+' dias).</p>'+
      '<p>Equivale a <strong>'+sign+hours.toLocaleString('pt-BR')+'</strong> horas, <strong>'+sign+minutes.toLocaleString('pt-BR')+'</strong> minutos e <strong>'+sign+seconds.toLocaleString('pt-BR')+'</strong> segundos.</p>';
  }}
  document.addEventListener('DOMContentLoaded',function(){{
    document.getElementById('d2-run').addEventListener('click',calc);
  }});
}})();
</script>"""
    body += _ad("mid")
    body += """<section class="section"><div class="container container--narrow prose">
<h2>Para que serve</h2>
<p>Calcula o intervalo entre duas datas em várias unidades ao mesmo tempo. Funciona bem para acompanhar gestação (semanas e dias), contratos (anos e meses), projetos (dias) e curiosidades pessoais (horas e minutos vividos).</p>
<h2>Como calculamos</h2>
<p>Para anos, meses e dias de calendário fazemos a subtração componente a componente e ajustamos quando o dia ou o mês ficam negativos. Para dias corridos usamos a diferença direta entre as duas datas em milissegundos UTC. Horas, minutos e segundos vêm dos dias corridos.</p>
<h2>Exemplo</h2>
<p>Entre 2025-01-15 e 2026-06-11 há 1 ano, 4 meses e 27 dias (511 dias corridos, 73 semanas).</p>
</div></section>"""
    body += _related_grid(slug)

    faq = [
        ("A ordem das datas importa?",
         "Não. A ferramenta calcula a diferença absoluta; se a Data 2 for anterior, mostramos o sinal negativo nos totais para indicar a direção."),
        ("Por que o total em dias é diferente da soma de anos × 365 + meses × 30?",
         "Meses têm 28 a 31 dias e anos têm 365 ou 366 dias. O total real só sai da subtração direta das duas datas no calendário."),
        ("Devo marcar 'incluir a data final'?",
         "Marque sim quando o último dia também conta no prazo (por exemplo, contagem inclusiva exigida em alguns contratos). Para a maioria dos usos, deixe em 'Não'."),
        ("Posso usar para idade gestacional?",
         "Sim. Use a data da última menstruação como Data 1 e a data atual como Data 2. A linha de semanas e dias dá uma boa estimativa, mas para acompanhamento médico use sempre a ultrassonografia."),
        ("Funciona para datas no passado distante?",
         "Sim. A diferença é calculada sobre o calendário gregoriano usado no Brasil."),
        ("Por que não conto dias úteis aqui?",
         "Para dias úteis use a calculadora dedicada, que considera fins de semana e feriados nacionais ou bancários."),
    ]
    breadcrumbs = [("Início", "index.html"), ("Diferença entre datas", "")]
    _write(out_dir, layout_fn, slug, title, description, body, breadcrumbs, faq)


# -- countdown.html ---------------------------------------------------------

def render_countdown(out_dir: Path, layout_fn, **deps) -> None:
    slug = "countdown.html"
    title = "Contagem Regressiva - tempo restante até uma data"
    description = (
        "Contagem regressiva ao vivo até a data alvo, com dias, horas, minutos e "
        "segundos. Inclui permalink compartilhável e dia da semana."
    )

    body = _hero(
        layout_fn,
        "Contagem Regressiva",
        "Quanto tempo falta para uma data importante? Veja dias, horas, minutos e "
        "segundos ao vivo, com permalink compartilhável.",
        primary_href="proximo-feriado.html",
        primary_label="Próximo feriado",
        ghost_href="diferenca-entre-datas.html",
        ghost_label="Diferença entre datas",
    )
    body += _ad("header")
    body += """<section class="section"><div class="container"><div class="tool" data-tool="countdown">
<div class="tool-grid">
<div class="field"><label for="cd-date">Data alvo</label><input id="cd-date" type="date"></div>
<div class="field"><label for="cd-name">Nome do evento (opcional)</label><input id="cd-name" type="text" placeholder="ex.: Aniversário"></div>
</div>
<button class="btn btn--primary" id="cd-run" type="button">Iniciar contagem</button>
<div class="result-box" id="cd-result" hidden aria-live="polite" aria-atomic="true"></div>
<p class="muted" id="cd-link" hidden></p>
</div></div></section>
<script>
(function(){
  var WEEKDAYS_LONG=['domingo','segunda-feira','terça-feira','quarta-feira','quinta-feira','sexta-feira','sábado'];
  function parseLocal(s){var p=(s||'').split('-').map(Number);if(p.length!==3)return null;return new Date(p[0],p[1]-1,p[2]);}
  function pad(n){return n<10?'0'+n:''+n;}
  function esc(s){var d=document.createElement('span');d.textContent=String(s||'');return d.innerHTML;}
  var timer=null;
  function tick(target,name){
    var now=new Date();
    var diff=target-now;
    var box=document.getElementById('cd-result');
    box.hidden=false;
    if(diff<=0){
      if(timer){clearInterval(timer);timer=null;}
      box.innerHTML='<p><strong>'+esc(name||'O evento')+'</strong> já chegou!</p>';
      return;
    }
    var totalSec=Math.floor(diff/1000);
    var days=Math.floor(totalSec/86400);
    var hours=Math.floor((totalSec%86400)/3600);
    var minutes=Math.floor((totalSec%3600)/60);
    var seconds=totalSec%60;
    var weekday=WEEKDAYS_LONG[target.getDay()];
    box.innerHTML=
      '<p style="font-size:1.4rem;margin:0"><strong>'+(name?esc(name)+': ':'')+
      days+'</strong> dia(s), <strong>'+pad(hours)+'</strong> h, <strong>'+pad(minutes)+'</strong> min, <strong>'+pad(seconds)+'</strong> s.</p>'+
      '<p class="muted">A data alvo cai em uma '+weekday+'.</p>';
  }
  function start(){
    var v=document.getElementById('cd-date').value;
    var target=parseLocal(v);
    var name=document.getElementById('cd-name').value.trim().slice(0,80);
    if(!target){document.getElementById('cd-result').hidden=false;document.getElementById('cd-result').textContent='Informe a data alvo.';return;}
    if(timer){clearInterval(timer);}
    tick(target,name);
    timer=setInterval(function(){tick(target,name);},1000);
    var qs='?d='+encodeURIComponent(v)+(name?'&e='+encodeURIComponent(name):'');
    var url=location.origin+location.pathname+qs;
    history.replaceState(null,'',qs);
    var link=document.getElementById('cd-link');
    link.hidden=false;
    link.textContent='Permalink: ';
    var a=document.createElement('a');a.href=url;a.textContent=url;
    link.appendChild(a);
  }
  document.addEventListener('DOMContentLoaded',function(){
    var url=new URL(location.href);
    var d=url.searchParams.get('d');
    var e=(url.searchParams.get('e')||'').slice(0,80);
    if(d&&/^\d{4}-\d{2}-\d{2}$/.test(d)){document.getElementById('cd-date').value=d;}
    if(e){document.getElementById('cd-name').value=e;}
    document.getElementById('cd-run').addEventListener('click',start);
    if(d&&/^\d{4}-\d{2}-\d{2}$/.test(d)){start();}
  });
})();
</script>"""
    body += _ad("mid")
    body += """<section class="section"><div class="container container--narrow prose">
<h2>Para que serve</h2>
<p>Um cronômetro em formato regressivo, que mostra quantos dias, horas, minutos e segundos faltam para uma data importante. Funciona para aniversários, viagens, casamentos, exames, lançamentos e datas de entrega.</p>
<h2>Como calculamos</h2>
<p>A diferença entre o horário atual do navegador e a data alvo é convertida em dias, horas, minutos e segundos. Os números são recalculados a cada segundo. O permalink na URL guarda a data e o nome do evento para você compartilhar.</p>
<h2>Exemplo</h2>
<p>Para acompanhar quanto falta até 31 de dezembro, preencha a data e clique em iniciar contagem. A URL passa a conter <code>?d=2026-12-31</code> e pode ser enviada a outras pessoas.</p>
</div></section>"""
    body += _related_grid(slug)

    faq = [
        ("A contagem atualiza sozinha?",
         "Sim. Após iniciar, os números são recalculados a cada segundo enquanto a página estiver aberta."),
        ("Posso compartilhar a contagem?",
         "Sim. O permalink mostrado abaixo do resultado já inclui a data e o nome do evento; basta copiar e enviar."),
        ("A contagem usa horário de Brasília?",
         "Usamos o relógio do dispositivo. Se o relógio do navegador estiver correto e no fuso de Brasília, os números refletem o horário local."),
        ("E se a data já passou?",
         "Quando a data alvo é anterior ao horário atual, a calculadora avisa que o evento já chegou e para a contagem."),
        ("Posso usar para evento sem nome?",
         "Sim. O campo de nome é opcional; só serve para personalizar o resultado e o permalink."),
        ("A contagem funciona offline?",
         "Funciona. Toda a lógica está no navegador, então não precisa de conexão depois que a página é carregada."),
    ]
    breadcrumbs = [("Início", "index.html"), ("Contagem regressiva", "")]
    _write(out_dir, layout_fn, slug, title, description, body, breadcrumbs, faq)


# -- proximo-feriado.html ---------------------------------------------------

def render_proximo_feriado(out_dir: Path, layout_fn, **deps) -> None:
    """Render with the next 5 national holidays from today."""
    import generate_site as gs

    slug = "proximo-feriado.html"
    title = "Próximo Feriado Nacional - quando é, dias restantes"
    description = (
        "Veja qual é o próximo feriado nacional brasileiro, em quanto tempo "
        "chega e a lista dos próximos cinco feriados."
    )

    today = date.today()
    pool: list = []
    for year in (today.year, today.year + 1, today.year + 2):
        pool.extend(gs.national_holidays(year))
    upcoming = [h for h in pool if h.date >= today and h.official]
    upcoming.sort(key=lambda h: h.date)
    next5 = upcoming[:5]

    rows = []
    for h in next5:
        delta = (h.date - today).days
        wd = gs.WEEKDAYS_LONG[h.date.weekday()]
        bridge = ""
        if h.date.weekday() == 1:
            bridge = " · oportunidade de emenda na segunda"
        elif h.date.weekday() == 3:
            bridge = " · oportunidade de emenda na sexta"
        elif h.date.weekday() in (0, 4):
            bridge = " · feriado prolongado natural"
        rows.append(
            f"<tr><td>{gs.fmt_short(h.date)}</td><td>{wd}</td>"
            f"<td><strong>{html.escape(h.name)}</strong>{bridge}</td>"
            f"<td>{delta} dia(s)</td></tr>"
        )
    table = (
        '<div class="table-wrap"><table><thead><tr>'
        '<th>Data</th><th>Dia</th><th>Feriado</th><th>Faltam</th>'
        '</tr></thead><tbody>' + "".join(rows) + "</tbody></table></div>"
    )

    if next5:
        nxt = next5[0]
        delta = (nxt.date - today).days
        highlight = (
            f'<p style="font-size:1.4rem;margin:0">Próximo feriado: '
            f'<strong>{html.escape(nxt.name)}</strong> em '
            f'<strong>{gs.fmt_date(nxt.date)}</strong> '
            f'({gs.WEEKDAYS_LONG[nxt.date.weekday()]}).</p>'
            f'<p>Faltam <strong>{delta}</strong> dia(s).</p>'
        )
    else:
        highlight = '<p>Não encontramos feriados futuros na base atual.</p>'

    body = _hero(
        layout_fn,
        "Próximo Feriado Nacional",
        "Qual é o próximo feriado nacional brasileiro e em quanto tempo ele chega. "
        "Inclui a lista dos próximos cinco feriados.",
        primary_href=f"feriados-{today.year}.html",
        primary_label=f"Todos os feriados {today.year}",
        ghost_href="countdown.html",
        ghost_label="Contagem regressiva",
    )
    body += _ad("header")
    body += (
        '<section class="section"><div class="container"><div class="tool" data-tool="next-holiday">'
        + highlight
        + '<h2 style="margin-top:1.4rem">Próximos 5 feriados nacionais</h2>'
        + table
        + '</div></div></section>'
    )
    body += _ad("mid")
    body += """<section class="section"><div class="container container--narrow prose">
<h2>Para que serve</h2>
<p>Saber rapidamente qual é o próximo feriado nacional brasileiro, quantos dias faltam e em que dia da semana ele cai. Útil para planejar viagem, emenda e folga.</p>
<h2>Como calculamos</h2>
<p>Comparamos a data de hoje com a base de feriados nacionais dos próximos anos e ordenamos os mais próximos. Quando o feriado cai na terça ou quinta, sinalizamos a oportunidade de emendar a segunda ou a sexta.</p>
<h2>Exemplo</h2>
<p>Se hoje é meio de agosto, o próximo feriado nacional costuma ser o 7 de Setembro. A página mostra a data exata, o dia da semana e quantos dias faltam.</p>
</div></section>"""
    body += _related_grid(slug)

    faq = [
        ("A lista inclui feriados estaduais?",
         "Não. Listamos só feriados nacionais civis previstos em lei federal. Para datas locais consulte a página de estados e capitais."),
        ("Por que Carnaval e Corpus Christi não aparecem?",
         "Eles não são feriados nacionais civis: são ponto facultativo no calendário federal. Aparecem em outras páginas e no calendário bancário."),
        ("Como sei se vai dar para emendar?",
         "Quando o feriado cai numa terça, é comum emendar a segunda. Em quinta, emenda-se a sexta. A página sinaliza essa oportunidade ao lado do nome."),
        ("A lista considera Sexta-feira Santa?",
         "Sexta-feira Santa não é feriado nacional civil pela Lei nº 10.607. Aparece em páginas dedicadas e em calendários estaduais e bancários."),
        ("Quantos feriados aparecem?",
         "Mostramos o próximo em destaque e os cinco mais próximos em uma tabela com data, dia da semana e dias restantes."),
        ("Os dados estão atualizados?",
         "Sim. A página é gerada estaticamente a partir das leis vigentes; revisamos anualmente."),
    ]
    breadcrumbs = [("Início", "index.html"), ("Próximo feriado", "")]
    _write(out_dir, layout_fn, slug, title, description, body, breadcrumbs, faq)


# -- dia-da-semana.html -----------------------------------------------------

def render_dia_da_semana(out_dir: Path, layout_fn, **deps) -> None:
    today_iso = date.today().isoformat()
    slug = "dia-da-semana.html"
    title = "Dia da Semana - em qual dia cai uma data"
    description = (
        "Descubra em qual dia da semana qualquer data cai. Mostra também o "
        "número da semana ISO, dia do ano e a mesma data em outros anos."
    )

    body = _hero(
        layout_fn,
        "Dia da Semana de uma Data",
        "Em qual dia da semana caiu (ou cai) uma data? Veja também o número da "
        "semana ISO, o dia do ano e a mesma data nos próximos anos.",
        primary_href="numero-da-semana.html",
        primary_label="Número da semana",
        ghost_href="data-da-semana.html",
        ghost_label="Data da semana ISO",
    )
    body += _ad("header")
    body += f"""<section class="section"><div class="container"><div class="tool" data-tool="dia-semana">
<div class="tool-grid">
<div class="field"><label for="ds-date">Data</label><input id="ds-date" type="date" value="{today_iso}"></div>
</div>
<button class="btn btn--primary" id="ds-run" type="button">Ver dia da semana</button>
<div class="result-box" id="ds-result" hidden aria-live="polite" aria-atomic="true"></div>
</div></div></section>
<script>
(function(){{
  var WEEKDAYS_LONG=['domingo','segunda-feira','terça-feira','quarta-feira','quinta-feira','sexta-feira','sábado'];
  function parseUTC(s){{var p=(s||'').split('-').map(Number);if(p.length!==3)return null;return new Date(Date.UTC(p[0],p[1]-1,p[2]));}}
  function fmt(d){{return d.toLocaleDateString('pt-BR',{{timeZone:'UTC'}});}}
  function isoWeek(d){{
    var tmp=new Date(Date.UTC(d.getUTCFullYear(),d.getUTCMonth(),d.getUTCDate()));
    var day=tmp.getUTCDay()||7;
    tmp.setUTCDate(tmp.getUTCDate()+4-day);
    var yearStart=new Date(Date.UTC(tmp.getUTCFullYear(),0,1));
    return Math.ceil((((tmp-yearStart)/86400000)+1)/7);
  }}
  function dayOfYear(d){{
    var start=new Date(Date.UTC(d.getUTCFullYear(),0,1));
    return Math.floor((d-start)/86400000)+1;
  }}
  function calc(){{
    var d=parseUTC(document.getElementById('ds-date').value);
    var box=document.getElementById('ds-result');
    box.hidden=false;
    if(!d){{box.textContent='Informe uma data.';return;}}
    var wd=WEEKDAYS_LONG[d.getUTCDay()];
    var rows='';
    for(var off=-1;off<=5;off++){{
      var dy=new Date(Date.UTC(d.getUTCFullYear()+off,d.getUTCMonth(),d.getUTCDate()));
      var label=off===0?'<strong>'+fmt(dy)+' (referência)</strong>':fmt(dy);
      rows+='<tr><td>'+label+'</td><td>'+WEEKDAYS_LONG[dy.getUTCDay()]+'</td></tr>';
    }}
    box.innerHTML=
      '<p>'+fmt(d)+' cai em uma <strong>'+wd+'</strong>.</p>'+
      '<p>Semana ISO <strong>'+isoWeek(d)+'</strong> · dia <strong>'+dayOfYear(d)+'</strong> do ano.</p>'+
      '<div class="table-wrap"><table><thead><tr><th>Data</th><th>Dia da semana</th></tr></thead><tbody>'+rows+'</tbody></table></div>';
  }}
  document.addEventListener('DOMContentLoaded',function(){{
    document.getElementById('ds-run').addEventListener('click',calc);
  }});
}})();
</script>"""
    body += _ad("mid")
    body += """<section class="section"><div class="container container--narrow prose">
<h2>Para que serve</h2>
<p>Descobrir em que dia da semana caiu seu nascimento, um contrato antigo, uma data histórica ou uma data futura. A tabela mostra ainda a mesma data nos anos vizinhos, ótimo para planejar aniversários e agendas.</p>
<h2>Como calculamos</h2>
<p>Usamos a função interna de data do navegador em UTC, evitando problemas de fuso horário. O número da semana segue o padrão ISO 8601: semana 1 contém a primeira quinta-feira do ano.</p>
<h2>Exemplo</h2>
<p>02/05/1990 caiu em uma quarta-feira. A mesma data em 2026 será um sábado.</p>
</div></section>"""
    body += _related_grid(slug)

    faq = [
        ("A ferramenta funciona para datas históricas?",
         "Sim, desde que estejam no calendário gregoriano. Para datas anteriores a 1582 a conversão pode não refletir o calendário juliano usado na época."),
        ("O que é semana ISO?",
         "É um padrão internacional em que a semana começa na segunda-feira e a semana 1 do ano é aquela que contém a primeira quinta-feira do ano."),
        ("Por que a data muda de dia da semana a cada ano?",
         "Anos comuns têm 365 dias, que dão 52 semanas e 1 dia. Por isso o dia da semana avança 1 a cada ano (e 2 ao atravessar um 29 de fevereiro)."),
        ("A página mostra a mesma data em outros anos?",
         "Sim. Listamos do ano anterior até cinco anos depois para você comparar."),
        ("Posso colar a data em outro formato?",
         "O campo aceita o padrão do navegador (AAAA-MM-DD). Use o seletor para evitar dúvida."),
        ("Funciona para datas no fim do ano?",
         "Sim. Algumas datas do fim de dezembro podem cair na semana ISO 1 do ano seguinte; o cálculo segue a regra padrão."),
    ]
    breadcrumbs = [("Início", "index.html"), ("Dia da semana", "")]
    _write(out_dir, layout_fn, slug, title, description, body, breadcrumbs, faq)


# -- data-mais-dias.html ----------------------------------------------------

def render_data_mais_dias(out_dir: Path, layout_fn, **deps) -> None:
    today_iso = date.today().isoformat()
    slug = "data-mais-dias.html"
    title = "Data ± N Dias Corridos - calculadora de prazo"
    description = (
        "Adicione ou subtraia N dias corridos a uma data. Calcula prazos, "
        "vencimentos, gestação e contratos em dias corridos."
    )

    body = _hero(
        layout_fn,
        "Data ± N Dias Corridos",
        "Adicione ou subtraia N dias corridos a uma data inicial. Útil para "
        "prazos contratuais, vencimentos, gestação e datas futuras.",
        primary_href="adicionar-dias-uteis.html",
        primary_label="Versão em dias úteis",
        ghost_href="subtrair-dias-uteis.html",
        ghost_label="Subtrair dias úteis",
    )
    body += _ad("header")
    body += f"""<section class="section"><div class="container"><div class="tool" data-tool="dmd">
<div class="tool-grid">
<div class="field"><label for="dmd-start">Data inicial</label><input id="dmd-start" type="date" value="{today_iso}"></div>
<div class="field"><label for="dmd-op">Operação</label><select id="dmd-op"><option value="add">Adicionar (+)</option><option value="sub">Subtrair (-)</option></select></div>
<div class="field"><label for="dmd-days">Quantidade de dias corridos</label><input id="dmd-days" type="number" min="0" value="30"></div>
</div>
<button class="btn btn--primary" id="dmd-run" type="button">Calcular</button>
<div class="result-box" id="dmd-result" hidden aria-live="polite" aria-atomic="true"></div>
</div></div></section>
<script>
(function(){{
  var WEEKDAYS_LONG=['domingo','segunda-feira','terça-feira','quarta-feira','quinta-feira','sexta-feira','sábado'];
  function parseUTC(s){{var p=(s||'').split('-').map(Number);if(p.length!==3)return null;return new Date(Date.UTC(p[0],p[1]-1,p[2]));}}
  function fmt(d){{return d.toLocaleDateString('pt-BR',{{timeZone:'UTC'}});}}
  function calc(){{
    var start=parseUTC(document.getElementById('dmd-start').value);
    var op=document.getElementById('dmd-op').value;
    var n=Number((document.getElementById('dmd-days').value||'0').toString().replace(',','.'));
    var box=document.getElementById('dmd-result');
    box.hidden=false;
    if(!start||isNaN(n)||n<0){{box.textContent='Informe data e quantidade válida.';return;}}
    var sign=op==='sub'?-1:1;
    var result=new Date(start.getTime()+sign*n*86400000);
    var wd=WEEKDAYS_LONG[result.getUTCDay()];
    box.innerHTML=
      '<p>Resultado: <strong>'+fmt(result)+'</strong> ('+wd+').</p>'+
      '<p class="muted">'+fmt(start)+' '+(sign>0?'+':'-')+' '+n+' dia(s) corridos.</p>';
  }}
  document.addEventListener('DOMContentLoaded',function(){{
    document.getElementById('dmd-run').addEventListener('click',calc);
  }});
}})();
</script>"""
    body += _ad("mid")
    body += """<section class="section"><div class="container container--narrow prose">
<h2>Para que serve</h2>
<p>Calcula a data final após somar ou subtrair um número de dias corridos a partir de uma data inicial. Diferente da contagem em dias úteis, esta versão inclui fins de semana e feriados.</p>
<h2>Como calculamos</h2>
<p>Multiplicamos a quantidade de dias por 24 horas e somamos (ou subtraímos) ao instante UTC da data inicial. Isso elimina problemas de fuso horário e de horário de verão.</p>
<h2>Exemplo</h2>
<p>Para saber o vencimento 30 dias após 11 de junho de 2026, preencha a data, escolha adicionar e digite 30. O resultado é 11 de julho de 2026 (sábado).</p>
</div></section>"""
    body += _related_grid(slug)

    faq = [
        ("Qual a diferença para dias úteis?",
         "Dias corridos contam todos os dias da semana, incluindo sábado, domingo e feriados. Dias úteis ignoram fim de semana e feriados nacionais."),
        ("Posso subtrair dias?",
         "Sim. Escolha 'Subtrair' e a calculadora recua N dias corridos a partir da data inicial."),
        ("Para contagem de prazo do CPC, qual escolho?",
         "Prazos processuais costumam ser em dias úteis (CPC/2015). Use a calculadora de dias úteis para esse caso e confirme com o regimento aplicável."),
        ("Funciona para acompanhar gestação?",
         "Sim. Some 280 dias à data da última menstruação para uma estimativa da data provável de parto."),
        ("E para vencimento de boleto?",
         "Use a versão em dias corridos quando o contrato diz só 'dias' sem qualificar. Quando o contrato menciona 'dias úteis' ou 'dias bancários', use as ferramentas dedicadas."),
        ("Há limite no número de dias?",
         "Não. A calculadora aceita qualquer valor não negativo e mostra a data resultante."),
    ]
    breadcrumbs = [("Início", "index.html"), ("Data ± dias corridos", "")]
    _write(out_dir, layout_fn, slug, title, description, body, breadcrumbs, faq)


# -- subtrair-dias-uteis.html ----------------------------------------------

def render_subtrair_dias_uteis(out_dir: Path, layout_fn, **deps) -> None:
    today_iso = date.today().isoformat()
    slug = "subtrair-dias-uteis.html"
    title = "Subtrair Dias Úteis - calcule a data anterior"
    description = (
        "Recue N dias úteis a partir de uma data, considerando fins de semana "
        "e feriados nacionais brasileiros."
    )

    body = _hero(
        layout_fn,
        "Subtrair Dias Úteis",
        "Recue N dias úteis a partir de uma data final. Útil para descobrir até "
        "quando uma tarefa precisa começar para cumprir um prazo.",
        primary_href="adicionar-dias-uteis.html",
        primary_label="Adicionar dias úteis",
        ghost_href="calcular-dias-uteis.html",
        ghost_label="Calcular intervalo",
    )
    body += _ad("header")
    body += f"""<section class="section"><div class="container"><div class="tool" data-tool="sub">
<div class="tool-grid">
<div class="field"><label for="sub-start">Data final</label><input id="sub-start" type="date" value="{today_iso}"></div>
<div class="field"><label for="sub-days">Dias úteis a recuar</label><input id="sub-days" type="number" min="0" value="5"></div>
<div class="field"><label for="sub-mode">Calendário</label><select id="sub-mode"><option value="standard">Dias úteis nacionais</option><option value="bank">Dias úteis bancários</option></select></div>
</div>
<button class="btn btn--primary" id="sub-run" type="button">Calcular</button>
<div class="result-box" id="sub-result" hidden aria-live="polite" aria-atomic="true"></div>
</div></div></section>
<script>
(function(){{
  var data=window.CB_CALENDAR_DATA||{{}};
  var WEEKDAYS_LONG=['domingo','segunda-feira','terça-feira','quarta-feira','quinta-feira','sexta-feira','sábado'];
  function parseUTC(s){{var p=(s||'').split('-').map(Number);if(p.length!==3)return null;return new Date(Date.UTC(p[0],p[1]-1,p[2]));}}
  function isoDate(d){{return d.toISOString().slice(0,10);}}
  function fmt(d){{return d.toLocaleDateString('pt-BR',{{timeZone:'UTC'}});}}
  function addDays(d,n){{var x=new Date(d);x.setUTCDate(x.getUTCDate()+n);return x;}}
  function isWeekend(d){{var w=d.getUTCDay();return w===0||w===6;}}
  function excluded(year,mode){{
    var y=data.years&&data.years[String(year)];
    if(!y)return new Set();
    return new Set(mode==='bank'?y.bankExcluded:y.standardExcluded);
  }}
  function isUseful(d,mode){{
    if(isWeekend(d))return false;
    return !excluded(d.getUTCFullYear(),mode).has(isoDate(d));
  }}
  function calc(){{
    var start=parseUTC(document.getElementById('sub-start').value);
    var n=Number(document.getElementById('sub-days').value||0);
    var mode=document.getElementById('sub-mode').value;
    var box=document.getElementById('sub-result');
    box.hidden=false;
    if(!start||n<0){{box.textContent='Informe data e quantidade válida.';return;}}
    var d=new Date(start);
    var rem=n;
    var steps=0;
    while(rem>0&&steps<3650){{
      d=addDays(d,-1);
      steps++;
      if(isUseful(d,mode))rem--;
    }}
    if(rem>0){{box.textContent='Não foi possível recuar a quantidade pedida.';return;}}
    var corridos=Math.round((start-d)/86400000);
    var wd=WEEKDAYS_LONG[d.getUTCDay()];
    box.innerHTML=
      '<p>Data recuada: <strong>'+fmt(d)+'</strong> ('+wd+').</p>'+
      '<p class="muted">Foram '+corridos+' dia(s) corridos para recuar '+n+' dia(s) '+(mode==='bank'?'útil(eis) bancário(s)':'útil(eis)')+'.</p>';
  }}
  document.addEventListener('DOMContentLoaded',function(){{
    document.getElementById('sub-run').addEventListener('click',calc);
  }});
}})();
</script>"""
    body += _ad("mid")
    body += """<section class="section"><div class="container container--narrow prose">
<h2>Para que serve</h2>
<p>Quando você sabe o prazo final e quer descobrir até quando precisa começar, esta calculadora é o caminho inverso da adição de dias úteis. Útil para tribunais, contratos, processos administrativos e planejamento de equipe.</p>
<h2>Como calculamos</h2>
<p>Recuamos um dia por vez a partir da data final. Pulamos sábados, domingos e feriados nacionais (ou bancários, conforme o modo escolhido) até completar a quantidade pedida de dias úteis.</p>
<h2>Exemplo</h2>
<p>Para entregar um documento em 15 dias úteis antes de uma audiência marcada para 30/10/2026 (sexta), recuar 15 dias úteis devolve 09/10/2026 (sexta).</p>
</div></section>"""
    body += _related_grid(slug)

    faq = [
        ("Considera quais feriados?",
         "Por padrão, os feriados nacionais civis brasileiros. Mude para 'bancários' se o seu prazo seguir o calendário FEBRABAN/ANBIMA."),
        ("Considera feriados estaduais?",
         "Não nesta versão. Para uso jurídico estadual, verifique também o calendário forense local."),
        ("A data final entra na contagem?",
         "Não. Começamos a recuar a partir do dia anterior à data final informada."),
        ("Por que mostra dias corridos também?",
         "Para você ter o referencial entre o intervalo no calendário (com fins de semana e feriados) e o intervalo em dias úteis."),
        ("Posso recuar mais de 1.000 dias úteis?",
         "Sim. O limite interno cobre vários anos para evitar travamento, mas qualquer valor razoável funciona."),
        ("Vale para prazos do CPC?",
         "Pode servir como referência, mas o CPC tem regras específicas (intimação, suspensão de prazo, recesso). Confirme com a norma aplicável."),
    ]
    breadcrumbs = [("Início", "index.html"), ("Subtrair dias úteis", "")]
    _write(out_dir, layout_fn, slug, title, description, body, breadcrumbs, faq)


# -- data-da-semana.html ----------------------------------------------------

def render_data_da_semana(out_dir: Path, layout_fn, **deps) -> None:
    slug = "data-da-semana.html"
    title = "Data da Semana ISO - inverso do número da semana"
    description = (
        "Dado o ano, a semana ISO e o dia da semana, descubra a data exata. "
        "Útil para planejamento corporativo e agendas."
    )
    current_year = date.today().year

    body = _hero(
        layout_fn,
        "Data da Semana ISO",
        "Inverso do número da semana: dado o ano, a semana ISO e o dia da "
        "semana, retornamos a data exata.",
        primary_href="numero-da-semana.html",
        primary_label="Número da semana",
        ghost_href="dia-da-semana.html",
        ghost_label="Dia da semana",
    )
    body += _ad("header")
    body += f"""<section class="section"><div class="container"><div class="tool" data-tool="dsemana">
<div class="tool-grid">
<div class="field"><label for="dsi-year">Ano</label><input id="dsi-year" type="number" min="2020" max="2050" value="{current_year}"></div>
<div class="field"><label for="dsi-week">Semana ISO</label><input id="dsi-week" type="number" min="1" max="53" value="1"></div>
<div class="field"><label for="dsi-day">Dia da semana</label><select id="dsi-day">
<option value="1">Segunda-feira</option><option value="2">Terça-feira</option><option value="3">Quarta-feira</option><option value="4">Quinta-feira</option><option value="5">Sexta-feira</option><option value="6">Sábado</option><option value="7">Domingo</option>
</select></div>
</div>
<button class="btn btn--primary" id="dsi-run" type="button">Calcular data</button>
<div class="result-box" id="dsi-result" hidden aria-live="polite" aria-atomic="true"></div>
</div></div></section>
<script>
(function(){{
  var MONTHS=['janeiro','fevereiro','março','abril','maio','junho','julho','agosto','setembro','outubro','novembro','dezembro'];
  var WEEKDAYS_LONG=['domingo','segunda-feira','terça-feira','quarta-feira','quinta-feira','sexta-feira','sábado'];
  function fmt(d){{return d.getUTCDate()+' de '+MONTHS[d.getUTCMonth()]+' de '+d.getUTCFullYear();}}
  function isoWeeksInYear(year){{
    var dec28=new Date(Date.UTC(year,11,28));
    var day=dec28.getUTCDay()||7;
    var tmp=new Date(Date.UTC(dec28.getUTCFullYear(),dec28.getUTCMonth(),dec28.getUTCDate()+4-day));
    var yearStart=new Date(Date.UTC(tmp.getUTCFullYear(),0,1));
    return Math.ceil((((tmp-yearStart)/86400000)+1)/7);
  }}
  function dayOfYear(d){{
    var start=new Date(Date.UTC(d.getUTCFullYear(),0,1));
    return Math.floor((d-start)/86400000)+1;
  }}
  function calc(){{
    var year=parseInt(document.getElementById('dsi-year').value,10);
    var week=parseInt(document.getElementById('dsi-week').value,10);
    var day=parseInt(document.getElementById('dsi-day').value,10);
    var box=document.getElementById('dsi-result');
    box.hidden=false;
    if(!year||!week||!day){{box.textContent='Preencha todos os campos.';return;}}
    var maxW=isoWeeksInYear(year);
    if(week<1||week>maxW){{box.textContent='O ano '+year+' tem '+maxW+' semanas ISO.';return;}}
    var jan4=new Date(Date.UTC(year,0,4));
    var jan4Day=jan4.getUTCDay()||7;
    var mondayWeek1=new Date(Date.UTC(year,0,4-(jan4Day-1)));
    var target=new Date(mondayWeek1.getTime()+((week-1)*7+(day-1))*86400000);
    var wd=WEEKDAYS_LONG[target.getUTCDay()];
    box.innerHTML=
      '<p>Data: <strong>'+fmt(target)+'</strong> ('+wd+').</p>'+
      '<p>Mês: <strong>'+MONTHS[target.getUTCMonth()]+'</strong> · dia <strong>'+dayOfYear(target)+'</strong> do ano de '+target.getUTCFullYear()+'.</p>';
  }}
  document.addEventListener('DOMContentLoaded',function(){{
    document.getElementById('dsi-run').addEventListener('click',calc);
  }});
}})();
</script>"""
    body += _ad("mid")
    body += """<section class="section"><div class="container container--narrow prose">
<h2>Para que serve</h2>
<p>Quando uma equipe se planeja em sprints ou semanas comerciais, é comum dizer 'semana 27, quinta-feira' em vez de uma data específica. Esta ferramenta faz o caminho inverso e devolve a data exata.</p>
<h2>Como calculamos</h2>
<p>Pelo padrão ISO 8601, a semana 1 do ano é a que contém o 4 de janeiro. A partir da segunda-feira dessa semana, somamos (semana − 1) × 7 dias mais (dia − 1) para chegar ao dia desejado.</p>
<h2>Exemplo</h2>
<p>Semana 27 de 2027, quinta-feira (dia 4): retorna 8 de julho de 2027.</p>
</div></section>"""
    body += _related_grid(slug)

    faq = [
        ("O que é a semana ISO?",
         "É o padrão internacional de numeração de semanas em que a semana 1 é aquela com a primeira quinta-feira do ano, e cada semana começa na segunda-feira."),
        ("Por que segunda-feira é o dia 1?",
         "Porque o padrão ISO 8601 começa a semana na segunda-feira. Domingo é o dia 7."),
        ("Quantas semanas ISO um ano pode ter?",
         "A maioria dos anos tem 52 semanas; alguns têm 53. A ferramenta avisa quando a semana informada não existe naquele ano."),
        ("Posso usar para qualquer ano?",
         "Aceitamos de 2020 a 2050. Para outros anos a regra é a mesma; é só ajustar o limite no formulário."),
        ("A primeira semana pode cair no ano anterior?",
         "Sim. Como a semana 1 contém o 4 de janeiro, ela pode começar em 29, 30 ou 31 de dezembro do ano anterior."),
        ("Para que ajuda no trabalho?",
         "Cronogramas, calendários comerciais europeus, sprints quinzenais e relatórios financeiros em base semanal usam muito a semana ISO."),
    ]
    breadcrumbs = [("Início", "index.html"), ("Data da semana ISO", "")]
    _write(out_dir, layout_fn, slug, title, description, body, breadcrumbs, faq)


# -- driver -----------------------------------------------------------------

EXTRA_TOOL_SLUGS = [
    "calculadora-idade.html",
    "diferenca-entre-datas.html",
    "countdown.html",
    "proximo-feriado.html",
    "dia-da-semana.html",
    "data-mais-dias.html",
    "subtrair-dias-uteis.html",
    "data-da-semana.html",
]


def render_all(out_dir: Path, layout_fn: Callable, **deps) -> list[str]:
    """Render all 8 extra tool pages. Returns the list of created slugs."""
    out_dir = Path(out_dir)
    render_calculadora_idade(out_dir, layout_fn, **deps)
    render_diferenca_entre_datas(out_dir, layout_fn, **deps)
    render_countdown(out_dir, layout_fn, **deps)
    render_proximo_feriado(out_dir, layout_fn, **deps)
    render_dia_da_semana(out_dir, layout_fn, **deps)
    render_data_mais_dias(out_dir, layout_fn, **deps)
    render_subtrair_dias_uteis(out_dir, layout_fn, **deps)
    render_data_da_semana(out_dir, layout_fn, **deps)
    return list(EXTRA_TOOL_SLUGS)
