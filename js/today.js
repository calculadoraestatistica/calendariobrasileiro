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
    var MESES=['Janeiro','Fevereiro','Mar\u00e7o','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'];
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
      div.innerHTML='<h3>Feriados deste m\u00eas</h3><ul>'+lis+'</ul>';
      var its=div.querySelectorAll('li span');
      for(var f=0;f<its.length;f++)its[f].textContent=monthHols[f].name;
      if(box)box.replaceWith(div);else if(noh)noh.replaceWith(div);else panel.appendChild(div);
    }else{
      var p=document.createElement('p');
      p.className='quick-panel__nohol muted';
      p.textContent='Sem feriados nacionais neste m\u00eas.';
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
