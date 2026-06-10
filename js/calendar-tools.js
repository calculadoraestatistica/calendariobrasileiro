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
