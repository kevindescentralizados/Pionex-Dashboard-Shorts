<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Descentralizados · Dashboard operativa short</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=DM+Sans:opsz,wght@9..40,400;9..40,500&family=Geist+Mono:wght@400;500&family=DM+Serif+Text:ital@1&display=swap" rel="stylesheet">
<style>
  :root{
    --noir:#141015; --noir2:#1B161D; --panel:#1F1A22; --panel2:#241E27;
    --line:#332C36; --line2:#473E4B;
    --thassos:#DCDCDC; --muted:#948C98; --muted2:#6E6573;
    --persimon:#F76E47; --persimon-dim:#9c4a32;
    --cobalt:#5C939F; --uranium:#CBA651;
    --pos:#F76E47; --neg:#5C939F;
    --mono:'Geist Mono',ui-monospace,monospace;
    --disp:'Space Grotesk',sans-serif;
    --body:'DM Sans',sans-serif;
  }
  *{box-sizing:border-box;margin:0;padding:0}
  html{scroll-behavior:smooth}
  body{
    background:var(--noir); color:var(--thassos); font-family:var(--body);
    font-size:15px; line-height:1.5; -webkit-font-smoothing:antialiased;
    background-image:radial-gradient(var(--line) 0.75px, transparent 0.75px);
    background-size:22px 22px; background-position:0 0;
  }
  .wrap{max-width:1240px; margin:0 auto; padding:38px 26px 80px}
  .kicker{font-family:var(--mono); font-size:12px; line-height:18px; letter-spacing:.06em;
    text-transform:uppercase; color:var(--persimon)}
  .kicker::before{content:"[ "} .kicker::after{content:" ]"}
  /* header */
  header.top{display:flex; justify-content:space-between; align-items:flex-end; gap:24px;
    flex-wrap:wrap; padding-bottom:26px; border-bottom:1px solid var(--line); margin-bottom:34px}
  .brandmark{display:flex; align-items:center; gap:11px; margin-bottom:18px}
  .brandmark .gear{width:26px;height:26px;flex:none}
  .brandmark .wm{font-family:var(--disp); font-weight:700; font-size:20px; letter-spacing:-.01em; color:var(--thassos)}
  h1{font-family:var(--disp); font-weight:700; font-size:46px; line-height:1.04; letter-spacing:-.02em;
    color:#fff; margin-top:14px; max-width:16ch}
  h1 .em{color:var(--persimon)}
  .sub{color:var(--muted); font-size:14px; margin-top:10px; max-width:46ch}
  .legend-side{font-family:var(--mono); font-size:11.5px; color:var(--muted2); text-align:right; line-height:1.9}
  .legend-side b{color:var(--thassos); font-weight:500}
  /* kpi */
  .kpis{display:grid; grid-template-columns:repeat(4,1fr); gap:16px; margin-bottom:18px}
  .kpi{background:var(--panel); border:1px solid var(--line); border-radius:14px; padding:20px 20px 18px; position:relative; overflow:hidden}
  .kpi::after{content:""; position:absolute; left:0; top:0; height:3px; width:100%; background:var(--persimon); opacity:.0}
  .kpi.accent::after{opacity:1}
  .kpi .lbl{font-family:var(--mono); font-size:11px; text-transform:uppercase; letter-spacing:.05em; color:var(--muted)}
  .kpi .val{font-family:var(--disp); font-weight:700; font-size:38px; line-height:1.05; margin-top:14px; letter-spacing:-.02em}
  .kpi .val.pos{color:var(--persimon)} .kpi .val.neg{color:var(--cobalt)}
  .kpi .note{font-family:var(--mono); font-size:11px; color:var(--muted2); margin-top:9px; line-height:1.6}
  .kpi .note b{color:var(--muted); font-weight:500}
  .callouts{display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:30px}
  .callout{background:var(--noir2); border:1px solid var(--line); border-radius:12px; padding:13px 18px;
    display:flex; justify-content:space-between; align-items:center; gap:14px}
  .callout .c-l{font-family:var(--mono); font-size:11px; text-transform:uppercase; letter-spacing:.05em; color:var(--muted)}
  .callout .c-d{font-family:var(--mono); font-size:12px; color:var(--muted2)}
  .callout .c-v{font-family:var(--disp); font-weight:700; font-size:20px}
  /* sections */
  section{margin-bottom:34px}
  .sec-head{display:flex; align-items:baseline; gap:14px; margin-bottom:16px}
  .sec-head h2{font-family:var(--disp); font-weight:600; font-size:21px; letter-spacing:-.01em; color:#fff}
  .charts{display:grid; grid-template-columns:1fr 360px; gap:18px}
  .card{background:var(--panel); border:1px solid var(--line); border-radius:14px; padding:22px}
  .card .ch-title{font-family:var(--mono); font-size:11px; text-transform:uppercase; letter-spacing:.05em; color:var(--muted); margin-bottom:6px}
  .card .ch-note{font-size:12.5px; color:var(--muted2); margin-bottom:14px}
  /* bar chart */
  #bars{width:100%; height:300px; display:block}
  .bar{cursor:pointer; transition:opacity .12s}
  .bar:hover{opacity:.72}
  .axis-line{stroke:var(--line2); stroke-width:1}
  .axis-txt{font-family:var(--mono); font-size:10px; fill:var(--muted2)}
  .zero-txt{font-family:var(--mono); font-size:10px; fill:var(--muted)}
  #tip{position:fixed; pointer-events:none; opacity:0; transform:translate(-50%,-120%);
    background:#0d0a0e; border:1px solid var(--line2); border-radius:8px; padding:8px 11px;
    font-family:var(--mono); font-size:11.5px; color:var(--thassos); z-index:50; white-space:nowrap;
    transition:opacity .1s}
  #tip b{font-weight:500} #tip .tp{color:var(--persimon)} #tip .tn{color:var(--cobalt)}
  /* donut */
  .donut-wrap{display:flex; flex-direction:column; align-items:center; gap:18px}
  #donut{width:212px;height:212px}
  .dn-center{font-family:var(--disp); font-weight:700}
  .leg{display:flex; flex-direction:column; gap:9px; width:100%}
  .leg .row{display:flex; align-items:center; gap:10px; font-family:var(--mono); font-size:12.5px}
  .leg .dot{width:11px;height:11px;border-radius:3px;flex:none}
  .leg .nm{color:var(--thassos)} .leg .ct{margin-left:auto; color:var(--muted)}
  /* daily breakdown */
  .controls{margin-left:auto; display:flex; gap:8px}
  .btn{font-family:var(--mono); font-size:11px; text-transform:uppercase; letter-spacing:.04em;
    color:var(--muted); background:var(--panel); border:1px solid var(--line); border-radius:8px;
    padding:7px 12px; cursor:pointer; transition:.12s}
  .btn:hover{border-color:var(--line2); color:var(--thassos)}
  .btn:focus-visible{outline:2px solid var(--persimon); outline-offset:2px}
  .day{background:var(--panel); border:1px solid var(--line); border-radius:12px; margin-bottom:10px; overflow:hidden}
  .day-h{display:flex; align-items:center; gap:16px; padding:14px 18px; cursor:pointer; user-select:none}
  .day-h:hover{background:var(--panel2)}
  .day-h:focus-visible{outline:2px solid var(--persimon); outline-offset:-2px}
  .day-date{font-family:var(--mono); font-size:13px; color:var(--thassos); min-width:108px}
  .day-meta{font-family:var(--mono); font-size:11px; color:var(--muted2)}
  .day-spacer{flex:1}
  .day-pct{font-family:var(--mono); font-size:12.5px; min-width:78px; text-align:right}
  .day-net{font-family:var(--disp); font-weight:700; font-size:18px; min-width:128px; text-align:right}
  .chev{width:14px;height:14px; transition:transform .18s; color:var(--muted)}
  .day.open .chev{transform:rotate(90deg)}
  .ops{display:none; border-top:1px solid var(--line); padding:4px 8px 8px}
  .day.open .ops{display:block}
  table{width:100%; border-collapse:collapse}
  th{font-family:var(--mono); font-size:10px; text-transform:uppercase; letter-spacing:.05em; color:var(--muted2);
    text-align:left; padding:9px 10px 7px; font-weight:400}
  th.r,td.r{text-align:right}
  td{padding:8px 10px; font-size:13.5px; border-top:1px solid var(--noir2)}
  tr:first-child td{border-top:none}
  .asset{font-family:var(--disp); font-weight:500; color:var(--thassos)}
  .num{font-family:var(--mono); font-size:12.5px}
  .pos{color:var(--persimon)} .neg{color:var(--cobalt)}
  .tag{font-family:var(--mono); font-size:9.5px; text-transform:uppercase; letter-spacing:.04em;
    padding:2px 7px; border-radius:5px; border:1px solid var(--line2); color:var(--muted)}
  .tag.reb{color:var(--cobalt); border-color:#314a50}
  .tag.rev{color:var(--uranium); border-color:#5a4d2c}
  .ent{display:inline-flex; align-items:center; gap:6px}
  .ent .pill{font-family:var(--mono); font-size:11px; color:var(--persimon); border:1px solid var(--persimon-dim);
    border-radius:20px; padding:1px 9px}
  .ent .pillm{color:var(--cobalt); border-color:#314a50}
  footer{margin-top:46px; padding-top:22px; border-top:1px solid var(--line);
    font-family:var(--mono); font-size:11px; color:var(--muted2); line-height:1.8}
  @media(max-width:900px){
    .kpis{grid-template-columns:1fr 1fr} .charts{grid-template-columns:1fr}
    h1{font-size:34px} .callouts{grid-template-columns:1fr}
    .day-meta{display:none} .day-pct{min-width:64px}
  }
  @media(max-width:560px){
    .kpis{grid-template-columns:1fr} .wrap{padding:26px 16px 60px}
    .day-net{font-size:16px; min-width:96px}
  }
  @media(prefers-reduced-motion:reduce){*{transition:none!important; scroll-behavior:auto!important}}
</style>
</head>
<body>
<div class="wrap">
  <header class="top">
    <div>
      <div class="brandmark">
        <svg class="gear" viewBox="0 0 32 32" fill="none" aria-hidden="true">
          <g fill="#DCDCDC">
            <circle cx="16" cy="16" r="3.4"/>
            <g>
              <rect x="14.6" y="1.5" width="2.8" height="7" rx="1.4"/>
              <rect x="14.6" y="23.5" width="2.8" height="7" rx="1.4"/>
              <rect x="1.5" y="14.6" width="7" height="2.8" rx="1.4"/>
              <rect x="23.5" y="14.6" width="7" height="2.8" rx="1.4"/>
            </g>
            <g transform="rotate(45 16 16)">
              <rect x="14.6" y="3.5" width="2.8" height="6" rx="1.4"/>
              <rect x="14.6" y="22.5" width="2.8" height="6" rx="1.4"/>
              <rect x="3.5" y="14.6" width="6" height="2.8" rx="1.4"/>
              <rect x="22.5" y="14.6" width="6" height="2.8" rx="1.4"/>
            </g>
          </g>
          <rect x="16" y="14.7" width="11" height="2.6" rx="1.3" fill="#F76E47" transform="rotate(8 16 16)"/>
        </svg>
        <span class="wm">descentralizados</span>
      </div>
      <div class="kicker">Método Cheng · Operativa short · Pionex Futures</div>
      <h1>Dashboard de <span class="em">resultados</span></h1>
      <p class="sub">389 operaciones cortas cerradas a lo largo de 94 días de mercado. Cifras netas: incluyen comisiones y funding.</p>
    </div>
    <div class="legend-side" id="legendSide"></div>
      <div class="legend-side" id="stamp" style="margin-top:8px"></div>
  </header>

  <div class="kpis" id="kpis"></div>
  <div class="callouts" id="callouts"></div>

  <section>
    <div class="sec-head"><span class="kicker">Gráficos</span><h2>Evolución y reparto</h2></div>
    <div class="charts">
      <div class="card">
        <div class="ch-title">PnL neto por día</div>
        <div class="ch-note" id="barNote"></div>
        <svg id="bars" role="img" aria-label="Gráfico de barras de PnL neto por día"></svg>
      </div>
      <div class="card">
        <div class="ch-title">Operaciones</div>
        <div class="ch-note">Ganadoras vs. perdedoras (neto)</div>
        <div class="donut-wrap">
          <svg id="donut" viewBox="0 0 120 120" role="img" aria-label="Gráfico circular ganadoras y perdedoras"></svg>
          <div class="leg" id="donutLeg"></div>
        </div>
      </div>
    </div>
  </section>

  <section>
    <div class="sec-head">
      <span class="kicker">Detalle</span><h2>Desglose por día</h2>
      <div class="controls">
        <button class="btn" id="expandAll">Expandir todo</button>
        <button class="btn" id="collapseAll">Plegar todo</button>
      </div>
    </div>
    <div id="days"></div>
  </section>

  <footer id="foot"></footer>
</div>
<div id="tip"></div>

<script>
function render(DATA){
  const K = DATA.kpi;

const eur = n => n.toLocaleString('es-ES',{minimumFractionDigits:2,maximumFractionDigits:2});
const sgn = n => (n>0?'+':'') + eur(n);
const money = n => sgn(n)+' $';
const pct = n => (n>0?'+':'')+n.toLocaleString('es-ES',{minimumFractionDigits:2,maximumFractionDigits:2})+'%';
const cls = n => n>0?'pos':(n<0?'neg':'');

/* KPI cards */
const kpis=[
  {lbl:'Balance neto total', val:money(K.total_net), c:cls(K.total_net), accent:true,
   note:`Bruto <b>${money(K.total_gross)}</b> · Comisiones <b>${money(K.total_fee)}</b> · Funding <b>${money(K.total_fund)}</b>`},
  {lbl:'Win rate', val:K.win_rate.toLocaleString('es-ES')+'%', c:'pos',
   note:`<b>${K.wins}</b> ganadoras · <b>${K.losses}</b> perdedoras · ${K.n_ops} ops`},
  {lbl:'Rentabilidad media', val:pct(K.avg_pct), c:cls(K.avg_pct),
   note:'Por operación · sobre operativa manual fiable'},
  {lbl:'Media de ganancia diaria', val:money(K.avg_daily), c:cls(K.avg_daily),
   note:`Neto ÷ <b>${K.ndays}</b> días operados`}
];
document.getElementById('kpis').innerHTML = kpis.map(k=>`
  <div class="kpi ${k.accent?'accent':''}">
    <div class="lbl">${k.lbl}</div>
    <div class="val ${k.c}">${k.val}</div>
    <div class="note">${k.note}</div>
  </div>`).join('');

document.getElementById('callouts').innerHTML = `
  <div class="callout"><div><div class="c-l">Mejor día</div><div class="c-d">${K.best.date}</div></div>
    <div class="c-v pos">${money(K.best.net)}</div></div>
  <div class="callout"><div><div class="c-l">Peor día</div><div class="c-d">${K.worst.date}</div></div>
    <div class="c-v neg">${money(K.worst.net)}</div></div>`;

document.getElementById('legendSide').innerHTML =
  `<div><b>Ganancia</b> · Persimon</div><div><b>Pérdida</b> · Cobalt</div>
   <div style="margin-top:6px">94 días · 389 ops</div>`;

/* ---- BAR CHART (signed-sqrt scale) ---- */
const days = DATA.days;
const bars = document.getElementById('bars');
const BW = 1000, BH = 300, padT=14, padB=26, padL=8, padR=8;
bars.setAttribute('viewBox',`0 0 ${BW} ${BH}`);
const vals = days.map(d=>d.net);
const maxP = Math.max(0,...vals), maxN = Math.min(0,...vals);
const sq = v => Math.sign(v)*Math.sqrt(Math.abs(v));
const sP = sq(maxP), sN = sq(maxN);
const innerH = BH-padT-padB;
const zeroY = padT + innerH * (sP/((sP-sN)||1));
const scaleUp = v => (sP>0? (sq(v)/sP)*(zeroY-padT) : 0);
const scaleDn = v => (sN<0? (sq(v)/sN)*((padT+innerH)-zeroY) : 0);
const n=days.length, gap=2, bw=(BW-padL-padR-gap*(n-1))/n;
let svg='';
svg+=`<line class="axis-line" x1="${padL}" y1="${zeroY}" x2="${BW-padR}" y2="${zeroY}"/>`;
svg+=`<text class="zero-txt" x="${padL}" y="${zeroY-5}">0 $</text>`;
days.forEach((d,i)=>{
  const x=padL+i*(bw+gap);
  let h,y;
  if(d.net>=0){h=scaleUp(d.net); y=zeroY-h;}
  else{h=scaleDn(d.net); y=zeroY;}
  const col = d.net>=0?'var(--pos)':'var(--neg)';
  svg+=`<rect class="bar" x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${bw.toFixed(1)}" height="${Math.max(h,0.6).toFixed(1)}"
        fill="${col}" data-i="${i}" tabindex="0"></rect>`;
});
/* x labels: ~every 12 days */
days.forEach((d,i)=>{
  if(i% Math.ceil(n/8)===0){
    const x=padL+i*(bw+gap)+bw/2;
    svg+=`<text class="axis-txt" x="${x.toFixed(1)}" y="${BH-9}" text-anchor="middle">${d.date.slice(5)}</text>`;
  }
});
bars.innerHTML=svg;
document.getElementById('barNote').textContent =
  'Altura en escala comprimida (raíz) para que convivan los días pequeños y el atípico de '+K.worst.date+'. Valor real al pasar el ratón.';

const tip=document.getElementById('tip');
function showTip(e,i){
  const d=days[i];
  tip.innerHTML=`<b>${d.date}</b> · ${d.nops} op${d.nops>1?'s':''}<br>
    <span class="${d.net>=0?'tp':'tn'}">${money(d.net)}</span>${d.pct!==null?` · ${pct(d.pct)}`:''}`;
  tip.style.opacity=1;
  const ev = e.touches? e.touches[0]:e;
  tip.style.left=ev.clientX+'px'; tip.style.top=ev.clientY+'px';
}
bars.addEventListener('mousemove',e=>{const r=e.target.closest('.bar'); if(r){showTip(e,+r.dataset.i);} else tip.style.opacity=0;});
bars.addEventListener('mouseleave',()=>tip.style.opacity=0);
bars.addEventListener('focusin',e=>{const r=e.target.closest('.bar'); if(r){const b=r.getBoundingClientRect();showTip({clientX:b.x+b.width/2,clientY:b.y},+r.dataset.i);}});

/* ---- DONUT ---- */
const w=K.wins, l=K.losses, tot=w+l;
const donut=document.getElementById('donut');
const R=48, C=2*Math.PI*R, cx=60, cy=60;
const wFrac=w/tot, lFrac=l/tot;
let dn=`<circle cx="${cx}" cy="${cy}" r="${R}" fill="none" stroke="var(--neg)" stroke-width="15"/>`;
dn+=`<circle cx="${cx}" cy="${cy}" r="${R}" fill="none" stroke="var(--pos)" stroke-width="15"
     stroke-dasharray="${(C*wFrac).toFixed(2)} ${C.toFixed(2)}" stroke-dashoffset="0"
     transform="rotate(-90 ${cx} ${cy})" stroke-linecap="butt"/>`;
dn+=`<text class="dn-center" x="${cx}" y="${cy-2}" text-anchor="middle" font-size="22" fill="#fff">${K.win_rate.toLocaleString('es-ES')}%</text>`;
dn+=`<text x="${cx}" y="${cy+15}" text-anchor="middle" font-size="8" fill="var(--muted)" font-family="var(--mono)">WIN RATE</text>`;
donut.innerHTML=dn;
document.getElementById('donutLeg').innerHTML=`
  <div class="row"><span class="dot" style="background:var(--pos)"></span><span class="nm">Ganadoras</span><span class="ct">${w} · ${(wFrac*100).toLocaleString('es-ES',{maximumFractionDigits:1})}%</span></div>
  <div class="row"><span class="dot" style="background:var(--neg)"></span><span class="nm">Perdedoras</span><span class="ct">${l} · ${(lFrac*100).toLocaleString('es-ES',{maximumFractionDigits:1})}%</span></div>`;

/* ---- DAILY BREAKDOWN ---- */
const tagTxt={OK:'',Rebalanceo:'<span class="tag reb">Rebalanceo</span>',Revisar:'<span class="tag rev">Revisar</span>'};
const daysEl=document.getElementById('days');
daysEl.innerHTML = [...days].reverse().map(d=>{
  const rows=d.ops.map(o=>{
    const entHtml = o.n!==null
      ? `<span class="ent"><span class="pill ${o.est!=='OK'?'pillm':''}">${o.n}</span></span>`
      : '<span class="num" style="color:var(--muted2)">—</span>';
    const pctHtml = o.pct!==null ? `<span class="num ${cls(o.pct)}">${pct(o.pct)}</span>`
                                 : '<span class="num" style="color:var(--muted2)">n/d</span>';
    return `<tr>
      <td><span class="asset">${o.activo}</span> ${tagTxt[o.est]}</td>
      <td class="r">${entHtml}</td>
      <td class="r"><span class="num ${cls(o.net)}">${money(o.net)}</span></td>
      <td class="r">${pctHtml}</td></tr>`;
  }).join('');
  const dpct = d.pct!==null?`<span class="num ${cls(d.pct)}">${pct(d.pct)}</span>`:'<span class="num" style="color:var(--muted2)">n/d</span>';
  return `<div class="day">
    <div class="day-h" tabindex="0" role="button" aria-expanded="false">
      <svg class="chev" viewBox="0 0 16 16" fill="none"><path d="M6 4l4 4-4 4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>
      <span class="day-date">${d.date}</span>
      <span class="day-meta">${d.nops} op${d.nops>1?'s':''} · ${d.wins} G</span>
      <span class="day-spacer"></span>
      <span class="day-pct">${dpct}</span>
      <span class="day-net ${cls(d.net)}">${money(d.net)}</span>
    </div>
    <div class="ops">
      <table><thead><tr><th>Activo</th><th class="r">Entradas</th><th class="r">Ganancia neta</th><th class="r">Rent. %</th></tr></thead>
      <tbody>${rows}</tbody></table>
    </div></div>`;
}).join('');

function toggle(day,force){
  const open = force!==undefined?force:!day.classList.contains('open');
  day.classList.toggle('open',open);
  day.querySelector('.day-h').setAttribute('aria-expanded',open);
}
daysEl.addEventListener('click',e=>{const h=e.target.closest('.day-h'); if(h) toggle(h.parentElement);});
daysEl.addEventListener('keydown',e=>{
  if((e.key==='Enter'||e.key===' ')&&e.target.classList.contains('day-h')){e.preventDefault();toggle(e.target.parentElement);}
});
document.getElementById('expandAll').onclick=()=>document.querySelectorAll('.day').forEach(d=>toggle(d,true));
document.getElementById('collapseAll').onclick=()=>document.querySelectorAll('.day').forEach(d=>toggle(d,false));

document.getElementById('foot').innerHTML=
  `Fuente: histórico de posiciones + ejecuciones (fills) de Pionex Futures. PnL reconstruido y validado contra el extracto. `+
  `Entradas = nº de añadidos al short que promedian el precio. Operaciones marcadas <span class="tag reb">Rebalanceo</span> son estrategia automática `+
  `(el nº de órdenes no equivale a promedios manuales); <span class="tag rev">Revisar</span> = reentradas solapadas del mismo activo. `+
  `La ganancia en $ es exacta en todos los casos.`;

} /* fin render */

const REFRESH_MS = 5 * 60 * 1000; // 5 min
async function load(){
  try{
    const res = await fetch('./data.json?_=' + Date.now(), {cache:'no-store'});
    if(!res.ok) throw new Error('HTTP '+res.status);
    const DATA = await res.json();
    if(DATA.empty){ document.getElementById('days').innerHTML =
      '<div class="card" style="color:var(--muted)">Aún no hay operaciones en el store. Coloca tus CSV en seed/ y ejecuta el recolector.</div>'; return; }
    render(DATA);
    const stamp = DATA.generated_at || '';
    const el = document.getElementById('stamp');
    if(el) el.textContent = stamp ? ('Datos: ' + stamp) : '';
  }catch(err){
    const d = document.getElementById('days');
    if(d) d.innerHTML = '<div class="card" style="color:var(--neg)">No se pudo cargar data.json ('+err.message+'). '+
      'Sirve el sitio por HTTP (no abriendo el archivo directamente) o revisa el recolector.</div>';
    console.error(err);
  }
}
load();
setInterval(load, REFRESH_MS);

</script>
</body>
</html>