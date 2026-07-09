const DATA = JSON.parse(document.getElementById('raw-data').textContent);

const SECTOR_LABELS = {
  'TECHNOLOGY': 'Technology',
  'HEALTH CARE': 'Health Care',
  'INDUSTRIALS/ENERGY': 'Industrials & Energy',
  'FINANCIALS/CONSUMER': 'Financials & Consumer'
};
const SECTOR_ORDER = ['TECHNOLOGY','HEALTH CARE','INDUSTRIALS/ENERGY','FINANCIALS/CONSUMER'];
const SECTOR_COLORS = {
  'TECHNOLOGY': '#6EA8FF',
  'HEALTH CARE': '#4FC38A',
  'INDUSTRIALS/ENERGY': '#E0C24A',
  'FINANCIALS/CONSUMER': '#C48CE8'
};
const YEARS = ['2023','2024','2025','2026'];

let activeSector = 'ALL';
let searchTerm = '';
let sortMode = 'default';
let timeFilter = 'ALL';
let pageTab = 'coverage';

function fmtPct(v){
  if(v===null||v===undefined||isNaN(v)) return '—';
  const s = v>=0 ? '+' : '';
  return s + v.toFixed(1) + '%';
}
function pctClass(v){
  if(v===null||v===undefined||isNaN(v)) return '';
  return v>=0 ? 'pos':'neg';
}
function fmtDate(d){
  if(!d) return '—';
  const [y,m,day] = d.split('-');
  const months=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  return months[parseInt(m,10)-1] + " '" + y.slice(2);
}
function fmtPrice(v){
  return (v===null||v===undefined) ? '—' : '$'+v.toFixed(2);
}
function shortName(analyst){
  return analyst.split(',')[0].split(' ').pop();
}

/* ---------- Period helpers ---------- */
function inPeriod(h, period){
  if(period==='ALL') return true;
  return !!(h.report_key && h.report_key.startsWith(period));
}
function sliceForPeriod(a, period){
  return a.history.filter(h=>inPeriod(h, period));
}
function compoundReturn(entries){
  let cum=1.0, any=false;
  entries.forEach(h=>{ if(h.return!==null && h.return!==undefined){ cum*=(1+h.return); any=true; } });
  return any ? Math.round((cum-1)*1000)/10 : null;
}
function trailingReturn(history, n){
  return compoundReturn(history.slice(-n));
}
function halfSlices(a, year){
  const h1 = a.history.filter(h=>h.report_key && h.report_key.startsWith(year) && parseInt(h.report_key.split('-')[1],10)<=6);
  const h2 = a.history.filter(h=>h.report_key && h.report_key.startsWith(year) && parseInt(h.report_key.split('-')[1],10)>=7);
  return {h1,h2};
}
function churnRate(entries){
  if(entries.length===0) return null;
  const switches = entries.filter(h=>h.new_pick).length;
  return switches/entries.length;
}

/* Compute the row's contextual metrics given the current time filter */
function rowContext(a){
  if(timeFilter==='ALL'){
    const half = trailingReturn(a.history,6);
    const ytd = a.year_returns ? a.year_returns['2026'] : null;
    const lastH = a.history[a.history.length-1];
    return {
      m1: a.trailing_return, m1Label:'12mo',
      m2: a.total_return, m2Label:'all-time',
      picks: a.history.length,
      lastH: lastH,
      latestTicker: a.latest_ticker, latestPrice: a.latest_price, latestDate: a.latest_date,
      sortKeys: { ytd, half, picks: a.history.length, churn: churnRate(a.history), insight: a.total_return }
    };
  } else {
    const {h1,h2} = halfSlices(a, timeFilter);
    const slice = sliceForPeriod(a, timeFilter);
    const lastH = slice.length ? slice[slice.length-1] : null;
    const yy = timeFilter.slice(2);
    const periodReturn = compoundReturn(slice);
    return {
      m1: compoundReturn(h1), m1Label:'H1 \u2019'+yy,
      m2: compoundReturn(h2), m2Label:'H2 \u2019'+yy,
      picks: slice.length,
      lastH: lastH,
      latestTicker: lastH?lastH.ticker:null, latestPrice: lastH?lastH.price:null, latestDate: lastH?lastH.date:null,
      sortKeys: { ytd: periodReturn, half: compoundReturn(h1), picks: slice.length, churn: churnRate(slice), insight: periodReturn }
    };
  }
}

function buildMarquee(){
  let latestDate = null;
  DATA.forEach(a=>{ if(a.latest_date && (!latestDate || a.latest_date > latestDate)) latestDate = a.latest_date; });
  const items = DATA.filter(a=>a.latest_date===latestDate && a.latest_ticker);
  const build = () => items.map(a=>{
    const h = a.history[a.history.length-1];
    const r = h.return;
    const cls = r===null ? '' : (r>=0?'up':'down');
    const arrow = r===null ? (h.new_pick?'★':'') : (r>=0?'▲':'▼');
    const label = r===null ? (h.new_pick?'new idea':'—') : (r*100).toFixed(1)+'%';
    return `<span class="tick"><b>${a.latest_ticker}</b> <span class="${cls}">${arrow} ${label}</span><span class="sep">·</span>${a.analyst}</span>`;
  }).join('');
  const html = build() + build();
  document.getElementById('marquee').innerHTML = html || 'No recent picks found';
  document.getElementById('stat-range').textContent = 'Jan 2023 – ' + fmtDate(latestDate);
}

function sparklinePath(cum, w, h){
  if(!cum || cum.length < 2) return {path:''};
  const min = Math.min(...cum), max = Math.max(...cum);
  const range = (max-min) || 1;
  const step = w/(cum.length-1);
  const pts = cum.map((v,i)=>{
    const x = i*step;
    const y = h - ((v-min)/range)*h;
    return [x,y];
  });
  const path = pts.map((p,i)=> (i===0?'M':'L') + p[0].toFixed(1) + ',' + p[1].toFixed(1)).join(' ');
  return {path};
}

function renderSpark(a){
  const {path} = sparklinePath(a.cum, 78, 26);
  if(!path) return '';
  const color = a.total_return>=0 ? 'var(--pos)' : 'var(--neg)';
  return `<svg class="spark" viewBox="0 0 78 26" preserveAspectRatio="none">
    <path d="${path}" fill="none" stroke="${color}" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round"/>
  </svg>`;
}

function buildBigChart(a){
  const w = 560, h = 220, pad = 32;
  const dates = a.history.map(r=>r.date || r.report_key);
  const cum = a.cum.map(v=>(v-1)*100);
  if(cum.length < 2){
    return '<div class="etf-note">Not enough history to chart.</div>';
  }
  const min = Math.min(0, ...cum), max = Math.max(0, ...cum);
  const range = (max-min)||1;
  const stepX = (w-2*pad)/(cum.length-1);
  const xy = cum.map((v,i)=>[pad+i*stepX, h-pad-((v-min)/range)*(h-2*pad)]);
  const path = xy.map((p,i)=>(i===0?'M':'L')+p[0].toFixed(1)+','+p[1].toFixed(1)).join(' ');
  const zeroY = h-pad-((0-min)/range)*(h-2*pad);

  let lastYear=''; let gridlines='';
  dates.forEach((d,i)=>{
    const y = (d||'').slice(0,4);
    if(y!==lastYear && y){
      lastYear=y;
      const x = pad+i*stepX;
      gridlines += `<line x1="${x}" y1="${pad}" x2="${x}" y2="${h-pad}" stroke="var(--border-soft)" stroke-width="1"/>`;
      gridlines += `<text x="${x+3}" y="${h-10}" fill="var(--text-faint)" font-size="9" font-family="var(--font-mono)">${y}</text>`;
    }
  });

  let markers = '';
  a.history.forEach((hh,i)=>{
    if(hh.new_pick && i>0){
      markers += `<circle cx="${xy[i][0].toFixed(1)}" cy="${xy[i][1].toFixed(1)}" r="2.4" fill="var(--brass)"/>`;
    }
  });

  const color = cum[cum.length-1] >= 0 ? 'var(--pos)' : 'var(--neg)';

  return `<svg width="100%" viewBox="0 0 ${w} ${h}" preserveAspectRatio="xMidYMid meet">
    ${gridlines}
    <line x1="${pad}" y1="${zeroY}" x2="${w-pad}" y2="${zeroY}" stroke="var(--text-faint)" stroke-width="1" stroke-dasharray="2,3"/>
    <path d="${path}" fill="none" stroke="${color}" stroke-width="1.8"/>
    ${markers}
    <text x="${w-pad}" y="${Math.max(12,xy[xy.length-1][1]-8)}" fill="${color}" font-size="11" font-family="var(--font-mono)" text-anchor="end" font-weight="700">${fmtPct(cum[cum.length-1])}</text>
  </svg>`;
}

function buildStatStrip(a){
  const half = trailingReturn(a.history,6);
  const ytd = a.year_returns ? a.year_returns['2026'] : null;
  const cells = [
    ['All-Time', a.total_return],
    ['Trailing 12mo', a.trailing_return],
    ['Trailing 6mo', half],
    ['YTD 2026', ytd],
  ];
  return `<div class="stat-strip">${cells.map(([k,v])=>`
    <div class="cell"><span class="v ${pctClass(v)}">${fmtPct(v)}</span><span class="k">${k}</span></div>
  `).join('')}</div>`;
}

function buildHistoryTable(a){
  const withNext = a.history.map((h, i) => {
    const next = a.history[i + 1];
    // "next close" only makes sense if the position was still held next month —
    // if the ticker changed, there's nothing to show (that position was exited,
    // not carried forward, so no future price for it exists in this dataset)
    const nextClose = (next && next.ticker === h.ticker) ? next.price : null;
    const nextHeld = !!(next && next.ticker === h.ticker);
    const cumPct = a.cum && a.cum[i] !== undefined ? (a.cum[i]-1)*100 : null;
    return {...h, nextClose, nextHeld, hasNext: !!next, cumPct};
  });

  const rows = withNext.slice().reverse().map(h=>{
    const retPct = h.return===null? null : h.return*100;
    const badge = h.new_pick ? '<span class="new-badge" title="Ticker changed from the prior report">CHANGED</span>' : '';
    let nextCloseCell;
    if (h.nextClose !== null) {
      nextCloseCell = fmtPrice(h.nextClose);
    } else if (!h.hasNext) {
      nextCloseCell = '<span title="Most recent report — no following month yet">—</span>';
    } else {
      nextCloseCell = '<span title="Position was exited before the following report — no price was recorded for it">—</span>';
    }
    let retCell;
    if (retPct === null) {
      retCell = `<span class="${pctClass(retPct)}">${fmtPct(retPct)}</span>`;
    } else if (h.return_type === 'exit') {
      retCell = `<span class="${pctClass(retPct)}" title="Reflects ${h.exit_ticker}'s performance up to this report, before the switch to ${h.ticker} — not ${h.ticker}'s own return">${fmtPct(retPct)}<span class="exit-tag">exit: ${h.exit_ticker}</span></span>`;
    } else {
      retCell = `<span class="${pctClass(retPct)}">${fmtPct(retPct)}</span>`;
    }
    return `<tr>
      <td>${fmtDate(h.date)}</td>
      <td class="tk">${h.ticker||'—'}${badge}</td>
      <td class="co">${h.company||''}</td>
      <td>${fmtPrice(h.price)}</td>
      <td>${h.price_target!==null&&h.price_target!==undefined?'$'+h.price_target:'—'}</td>
      <td>${nextCloseCell}</td>
      <td class="${pctClass(retPct)}">${retCell}</td>
      <td class="${pctClass(h.cumPct)}" style="font-weight:700;">${fmtPct(h.cumPct)}</td>
    </tr>`;
  }).join('');
  return `<div class="history-scroll"><table class="history-table">
    <thead><tr><th>Report</th><th>Ticker</th><th>Company</th><th>Closing Price</th><th>Price Target</th><th>Next Month Close</th><th>Return</th><th>Overall Progress</th></tr></thead>
    <tbody>${rows}</tbody>
  </table></div>
  <div class="etf-note" style="margin-top:8px;"><b>Return</b> = this row's Closing Price compared to the <i>prior</i> report's price for the same ticker — a one-month snapshot, not cumulative. <b>Overall Progress</b> (bold, right-hand column) is the running total from the very first tracked report through this one — compound all the Returns up to this row and that's what you get; this is the number to watch if you're asking "how are they doing overall" rather than "how did last month go." "Next Month Close" is shown so you can verify the following row's return without scrolling — a dash there means the pick changed before the next report. Rows marked <b>exit: TICKER</b> show the performance of the position that got replaced that month (sourced separately, not from the monthly report itself) rather than the new pick's — the new pick doesn't have a return of its own until the following report.</div>`;
}

function buildEtfCompare(a){
  const hasSector = !!a.etf;
  const cols = hasSector ? [
    {key:'etf', label:a.etf, sub:a.etf_label},
    {key:'spx', label:'SPX', sub:'S&P 500 (broad market)'},
  ] : [
    {key:'spx', label:'SPX', sub:'S&P 500 (broad market)'},
  ];
  const rows = YEARS.map(y=>{
    const av = a.year_returns ? a.year_returns[y] : null;
    const cellVals = cols.map(c=>{
      if(c.key==='etf') return a.etf_returns ? a.etf_returns[y] : null;
      return a.spx_returns ? a.spx_returns[y] : null;
    });
    if(av===null && cellVals.every(v=>v===null)) return '';
    const maxAbs = Math.max(Math.abs(av||0), ...cellVals.map(v=>Math.abs(v||0)), 1);
    const bar = (v)=>{
      if(v===null||v===undefined) return '<span style="color:var(--text-faint)">—</span>';
      const pct = Math.min(100, Math.abs(v)/maxAbs*100);
      const color = v>=0 ? 'var(--pos)':'var(--neg)';
      const side = v>=0 ? `left:50%;` : `right:50%;`;
      return `<span class="bar-cell"><span class="${pctClass(v)}" style="min-width:52px;text-align:right;display:inline-block">${fmtPct(v)}</span>
        <span class="bar-track"><span class="bar-fill" style="${side}width:${pct/2}%;background:${color}"></span></span></span>`;
    };
    return `<tr><td class="label">${y}</td><td>${bar(av)}</td>${cellVals.map(v=>`<td>${bar(v)}</td>`).join('')}</tr>`;
  }).join('');
  const headCols = cols.map(c=>`<th>${c.label}</th>`).join('');
  const subLabel = hasSector
    ? `<span class="etf-name">${a.etf} <span style="color:var(--text-faint);font-weight:400">— ${a.etf_label||''}</span></span><span class="etf-sub">vs. sector ETF and S&P 500</span>`
    : `<span class="etf-name">S&P 500 <span style="color:var(--text-faint);font-weight:400">— broad market (no sector ETF on file yet)</span></span><span class="etf-sub">industry-average comparison</span>`;
  return `<div class="etf-compare">
    <div class="etf-compare-head">${subLabel}</div>
    <table class="yr-table">
      <thead><tr><th>Year</th><th>${shortName(a.analyst)}</th>${headCols}</tr></thead>
      <tbody>${rows || '<tr><td colspan="'+(2+cols.length)+'" style="text-align:center;color:var(--text-faint)">No overlapping year data.</td></tr>'}</tbody>
    </table>
  </div>`;
}

function renderDetail(a){
  return `<div class="detail-grid">
    <div class="chart-box">
      <div class="chart-title">Full career snapshot — all windows below use complete history, independent of the period filter above</div>
      ${buildStatStrip(a)}
      <div class="chart-title">Cumulative return following ${a.analyst}'s picks (compounded, held periods only)</div>
      ${buildBigChart(a)}
      <div class="etf-note">Brass dots mark a switch to a new pick. Gaps in the line reflect months where a switch occurred and no return could be attributed to the prior position.</div>
      ${buildEtfCompare(a)}
    </div>
    <div class="table-box">
      <div class="chart-title">Full pick history (${a.history.length} reports)</div>
      ${buildHistoryTable(a)}
    </div>
  </div>`;
}

function renderRow(a, idx){
  const ctx = a.ctx;
  const spark = renderSpark(a);
  const lastH = ctx.lastH;
  const newBadge = lastH && lastH.new_pick ? '<span class="new-badge" title="Ticker changed from the prior report">CHANGED</span>' : '';
  return `
  <div class="row" data-idx="${idx}">
    <div class="row-num">${idx+1}</div>
    <div class="row-name">
      <div class="an">${a.analyst}</div>
      <div class="sec">${a.sector_label||''} <span style="color:var(--brass-dim)">· vs ${a.etf ? a.etf : 'SPX'}</span></div>
    </div>
    <div class="row-pick">
      <span class="tk">${ctx.latestTicker||'—'}</span><span class="pr">${fmtPrice(ctx.latestPrice)}</span>${newBadge}
      <span class="co">${lastH && lastH.company ? lastH.company : ''}</span>
    </div>
    <div class="metric ${pctClass(ctx.m1)}">${fmtPct(ctx.m1)}<span class="lbl">${ctx.m1Label}</span></div>
    <div class="metric ${pctClass(ctx.m2)}">${fmtPct(ctx.m2)}<span class="lbl">${ctx.m2Label}</span></div>
    <div>${spark}</div>
    <div class="chev">›</div>
  </div>
  <div class="detail" id="detail-row-${idx}"></div>
  `;
}

function getFiltered(){
  let list = DATA.map(a=>Object.assign({}, a, {ctx: rowContext(a)}));
  if(timeFilter !== 'ALL') list = list.filter(a=>a.ctx.picks>0);
  if(activeSector !== 'ALL') list = list.filter(a=>a.sector_group===activeSector);
  if(searchTerm){
    const s = searchTerm.toLowerCase();
    list = list.filter(a=>
      a.analyst.toLowerCase().includes(s) ||
      (a.sector_label||'').toLowerCase().includes(s) ||
      (a.latest_ticker||'').toLowerCase().includes(s) ||
      a.history.some(h=> (h.ticker||'').toLowerCase() === s || (h.company||'').toLowerCase().includes(s))
    );
  }
  const NA_LOW = -1e9, NA_HIGH = 1e9;
  if(sortMode==='total_desc') list.sort((x,y)=>(y.total_return??NA_LOW)-(x.total_return??NA_LOW));
  else if(sortMode==='total_asc') list.sort((x,y)=>(x.total_return??NA_HIGH)-(y.total_return??NA_HIGH));
  else if(sortMode==='trailing_desc') list.sort((x,y)=>(y.trailing_return??NA_LOW)-(x.trailing_return??NA_LOW));
  else if(sortMode==='half_desc') list.sort((x,y)=>(y.ctx.sortKeys.half??NA_LOW)-(x.ctx.sortKeys.half??NA_LOW));
  else if(sortMode==='ytd_desc') list.sort((x,y)=>(y.ctx.sortKeys.ytd??NA_LOW)-(x.ctx.sortKeys.ytd??NA_LOW));
  else if(sortMode==='picks_desc') list.sort((x,y)=>y.ctx.sortKeys.picks-x.ctx.sortKeys.picks);
  else if(sortMode==='churn_desc') list.sort((x,y)=>(y.ctx.sortKeys.churn??-1)-(x.ctx.sortKeys.churn??-1));
  else if(sortMode==='churn_asc') list.sort((x,y)=>(x.ctx.sortKeys.churn??2)-(y.ctx.sortKeys.churn??2));
  else if(sortMode==='name') list.sort((x,y)=>x.analyst.localeCompare(y.analyst));
  return list;
}

function periodSuffix(){
  return timeFilter==='ALL' ? '' : ` <span style="color:var(--brass-dim);font-weight:400">· ${timeFilter}</span>`;
}

function sectorAvgLabel(group){
  const vals = group.map(a=>a.ctx.sortKeys.ytd).filter(v=>v!==null && v!==undefined);
  if(vals.length===0) return '';
  const avg = vals.reduce((s,v)=>s+v,0)/vals.length;
  return ` <span style="color:${pctClass(avg)==='pos'?'var(--pos)':'var(--neg)'};font-weight:400">avg ${fmtPct(avg)}</span>`;
}

function render(){
  const main = document.getElementById('main');
  const list = getFiltered();
  if(list.length===0){
    main.innerHTML = `<div class="empty">No analysts or picks match${timeFilter!=='ALL' ? ' '+timeFilter : ''} that search.</div>`;
    return;
  }
  let html='';
  let idxCounter = 0;
  const rowIndexMap = [];
  if(sortMode==='default' && activeSector==='ALL'){
    SECTOR_ORDER.forEach(sec=>{
      const group = list.filter(a=>a.sector_group===sec);
      if(group.length===0) return;
      html += `<div class="sector-heading">${SECTOR_LABELS[sec]} <span style="color:var(--text-faint);font-weight:400">(${group.length})</span>${sectorAvgLabel(group)}</div>`;
      group.forEach(a=>{ html += renderRow(a, idxCounter); rowIndexMap.push(a); idxCounter++; });
    });
  } else if(sortMode==='default'){
    html += `<div class="sector-heading">${SECTOR_LABELS[activeSector]} <span style="color:var(--text-faint);font-weight:400">(${list.length})</span>${sectorAvgLabel(list)}</div>`;
    list.forEach(a=>{ html += renderRow(a, idxCounter); rowIndexMap.push(a); idxCounter++; });
  } else {
    list.forEach(a=>{ html += renderRow(a, idxCounter); rowIndexMap.push(a); idxCounter++; });
  }
  main.innerHTML = html;
  attachRowHandlers(rowIndexMap);
}

function attachRowHandlers(rowIndexMap){
  document.querySelectorAll('.row').forEach(row=>{
    row.addEventListener('click', ()=>{
      const idx = parseInt(row.getAttribute('data-idx'));
      const a = rowIndexMap[idx];
      const detailEl = document.getElementById('detail-row-'+idx);
      const wasOpen = detailEl.classList.contains('show');
      document.querySelectorAll('.detail.show').forEach(d=>d.classList.remove('show'));
      document.querySelectorAll('.row.open').forEach(r=>r.classList.remove('open'));
      if(!wasOpen){
        detailEl.innerHTML = renderDetail(a);
        detailEl.classList.add('show');
        row.classList.add('open');
      }
    });
  });
}

function buildTabs(){
  const tabs = document.getElementById('tabs');
  let html = `<div class="tab active" data-sector="ALL">All</div>`;
  SECTOR_ORDER.forEach(sec=>{
    html += `<div class="tab" data-sector="${sec}">${SECTOR_LABELS[sec]}</div>`;
  });
  tabs.innerHTML = html;
  tabs.querySelectorAll('.tab').forEach(t=>{
    t.addEventListener('click', ()=>{
      tabs.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));
      t.classList.add('active');
      activeSector = t.getAttribute('data-sector');
      render();
    });
  });
}

function buildTimeTabs(){
  const el = document.getElementById('timeTabs');
  let html = `<div class="time-tab active" data-period="ALL">All Time</div>`;
  YEARS.forEach(y=> html += `<div class="time-tab" data-period="${y}">${y}</div>`);
  el.innerHTML = html;
  el.querySelectorAll('.time-tab').forEach(t=>{
    t.addEventListener('click', ()=>{
      el.querySelectorAll('.time-tab').forEach(x=>x.classList.remove('active'));
      t.classList.add('active');
      timeFilter = t.getAttribute('data-period');
      render();
      if(pageTab==='insights') renderInsights();
    });
  });
}

function buildPageTabs(){
  document.querySelectorAll('.page-tab').forEach(t=>{
    t.addEventListener('click', ()=>{
      document.querySelectorAll('.page-tab').forEach(x=>x.classList.remove('active'));
      t.classList.add('active');
      pageTab = t.getAttribute('data-page');
      const isInsights = pageTab==='insights';
      document.getElementById('coverage-controls').style.display = isInsights ? 'none':'flex';
      document.getElementById('main').style.display = isInsights ? 'none':'block';
      document.getElementById('insights').style.display = isInsights ? 'block':'none';
      if(isInsights) renderInsights();
    });
  });
}

function computeMomentum(n){
  const pool = DATA.filter(a=>a.history && a.history.length);
  const results = [];
  pool.forEach(a=>{
    const validReturns = a.history.filter(h=>h.return!==null && h.return!==undefined);
    if(validReturns.length < n) return;
    const lastN = validReturns.slice(-n);
    if(lastN.every(h=>h.return>0)){
      const compounded = (lastN.reduce((acc,h)=>acc*(1+h.return),1)-1)*100;
      results.push({analyst:a.analyst, sector_label:a.sector_label, lastN, compounded});
    }
  });
  results.sort((x,y)=>y.compounded-x.compounded);
  return results;
}

function updateMomentumCard(n){
  const label = document.getElementById('momentum-label');
  if(label) label.textContent = n + (n===1?' month':' months');
  const list = document.getElementById('momentum-list');
  if(!list) return;
  const results = computeMomentum(n);
  const countEl = document.getElementById('momentum-count');
  if(countEl) countEl.textContent = results.length;
  if(results.length===0){
    list.innerHTML = `<div style="color:var(--text-faint);font-family:var(--font-mono);font-size:12px;">No analyst currently has ${n} consecutive positive report${n>1?'s':''}.</div>`;
    return;
  }
  const half = Math.ceil(results.length/2);
  const col = (arr) => arr.map(r=>`<div class="ins-row">
    <div><span class="name">${r.analyst}</span><span class="sub">${r.sector_label||''} · streak: ${r.lastN.map(h=>'+'+(h.return*100).toFixed(0)+'%').join(', ')}</span></div>
    <span class="pos" style="font-weight:700">${fmtPct(r.compounded)}</span>
  </div>`).join('');
  list.innerHTML = `<div class="momentum-list-wrap"><div>${col(results.slice(0,half))}</div><div>${col(results.slice(half))}</div></div>`;
}

/* ================= INSIGHTS ================= */
function renderInsights(){
  const wrap = document.getElementById('insights');
  const pool = DATA.map(a=>Object.assign({}, a, {ctx: rowContext(a)})).filter(a=>a.ctx.picks>0);
  const periodLabel = timeFilter==='ALL' ? 'across the full tracked history (Jan 2023 \u2013 Jun \u201926)' : `in ${timeFilter}`;
  const periodShort = timeFilter==='ALL' ? 'all-time' : timeFilter;

  if(pool.length===0){
    wrap.innerHTML = `<div class="empty">No picks logged for ${timeFilter}.</div>`;
    return;
  }

  const withReturn = pool.filter(a=>a.ctx.sortKeys.insight!==null && a.ctx.sortKeys.insight!==undefined);
  const ranked = withReturn.slice().sort((x,y)=>y.ctx.sortKeys.insight-x.ctx.sortKeys.insight);
  const top5 = ranked.slice(0,5);
  const bottom5 = ranked.slice(-5).reverse();

  // sector scoreboard
  const sectorStats = SECTOR_ORDER.map(sec=>{
    const grp = withReturn.filter(a=>a.sector_group===sec);
    if(grp.length===0) return null;
    const avg = grp.reduce((s,a)=>s+a.ctx.sortKeys.insight,0)/grp.length;
    return {sec, avg, n: grp.length};
  }).filter(Boolean).sort((x,y)=>y.avg-x.avg);

  // churn
  const withChurn = pool.filter(a=>a.ctx.picks>=3 && a.ctx.sortKeys.churn!==null);
  const rotators = withChurn.slice().sort((x,y)=>y.ctx.sortKeys.churn-x.ctx.sortKeys.churn).slice(0,5);
  const loyalists = withChurn.slice().sort((x,y)=>x.ctx.sortKeys.churn-y.ctx.sortKeys.churn).slice(0,5);

  // crowded trades: ticker -> set of analysts, within period
  const tickerMap = {};
  pool.forEach(a=>{
    const seen = new Set();
    sliceForPeriod(a, timeFilter).forEach(h=>{
      if(!h.ticker) return;
      const key = h.ticker;
      if(seen.has(key)) return; // count each analyst once per ticker
      seen.add(key);
      if(!tickerMap[key]) tickerMap[key] = [];
      tickerMap[key].push(a.analyst);
    });
  });
  const crowded = Object.entries(tickerMap).filter(([t,arr])=>arr.length>=2).sort((a,b)=>b[1].length-a[1].length).slice(0,10);

  // narrative pieces
  const avgAll = withReturn.length ? (withReturn.reduce((s,a)=>s+a.ctx.sortKeys.ytd,0)/withReturn.length) : null;
  const bestSector = sectorStats[0];
  const worstSector = sectorStats[sectorStats.length-1];
  const topA = top5[0];
  const botA = bottom5[0];
  const topRotator = rotators[0];
  const topLoyalist = loyalists[0];
  const topCrowd = crowded[0];

  let narrative = `<p>`;
  if(avgAll!==null){
    narrative += `Across <b>${withReturn.length} analysts</b> with a computable return ${periodLabel}, the average pick moved <b>${fmtPct(avgAll)}</b>. `;
  }
  if(bestSector && worstSector && bestSector.sec !== worstSector.sec){
    narrative += `${SECTOR_LABELS[bestSector.sec]} led all coverage groups at <b>${fmtPct(bestSector.avg)}</b> on average, while ${SECTOR_LABELS[worstSector.sec]} lagged at <b>${fmtPct(worstSector.avg)}</b>. `;
  }
  if(topA){
    narrative += `${topA.analyst} posted the strongest ${periodShort} return on the desk at <b>${fmtPct(topA.ctx.sortKeys.insight)}</b>`;
    if(botA && botA.analyst !== topA.analyst){
      narrative += `, while ${botA.analyst} sits at the other end at <b>${fmtPct(botA.ctx.sortKeys.insight)}</b>. `;
    } else { narrative += `. `; }
  }
  if(topRotator){
    const pct = Math.round(topRotator.ctx.sortKeys.churn*100);
    narrative += `${topRotator.analyst} rotated ideas the most, switching tickers on <b>${pct}%</b> of reports`;
  }
  if(topLoyalist && topRotator && topLoyalist.analyst !== topRotator.analyst){
    const pct2 = Math.round(topLoyalist.ctx.sortKeys.churn*100);
    narrative += `, while ${topLoyalist.analyst} showed the most conviction, changing course on just <b>${pct2}%</b> of reports. `;
  } else { narrative += `. `; }
  if(topCrowd){
    narrative += `The most crowded idea ${periodLabel.replace('across the full tracked history','over the full history')} was <b>${topCrowd[0]}</b>, independently picked by ${topCrowd[1].length} different analysts (${topCrowd[1].map(shortName).join(', ')}).`;
  }
  narrative += `</p>`;

  const rowHtml = (a, showVal=true) => `<div class="ins-row">
    <div><span class="name">${a.analyst}</span><span class="sub">${a.sector_label||''}</span></div>
    ${showVal ? `<span class="${pctClass(a.ctx.sortKeys.insight)}" style="font-weight:700">${fmtPct(a.ctx.sortKeys.insight)}</span>` : ''}
  </div>`;

  const churnRowHtml = (a) => `<div class="ins-row">
    <div><span class="name">${a.analyst}</span><span class="sub">${a.ctx.picks} picks ${periodLabel.replace('across the full tracked history','tracked')}</span></div>
    <span style="font-weight:700;color:var(--text)">${Math.round(a.ctx.sortKeys.churn*100)}%</span>
  </div>`;

  const maxSectorAbs = Math.max(...sectorStats.map(s=>Math.abs(s.avg)), 1);
  const sectorBarsHtml = sectorStats.map(s=>{
    const pct = Math.min(100, Math.abs(s.avg)/maxSectorAbs*100);
    return `<div class="sector-bar-row">
      <div class="lbl">${SECTOR_LABELS[s.sec]}</div>
      <div class="sector-bar-track"><div class="sector-bar-fill" style="width:${pct}%;background:${SECTOR_COLORS[s.sec]}"></div></div>
      <div class="sector-bar-val ${pctClass(s.avg)}">${fmtPct(s.avg)}</div>
    </div>`;
  }).join('');

  const crowdedHtml = crowded.length ? crowded.map(([t,arr])=>
    `<span class="crowd-chip"><b>${t}</b><span>×${arr.length}</span></span>`
  ).join('') : `<div style="color:var(--text-faint);font-family:var(--font-mono);font-size:12px;">No ticker was independently picked by 2+ analysts ${periodLabel}.</div>`;

  wrap.innerHTML = `
    <div class="insight-narrative">${narrative}</div>
    <div class="insight-grid">
      <div class="insight-card"><h3>Top Returns · ${periodShort}</h3>${top5.length?top5.map(a=>rowHtml(a)).join(''):'<div style="color:var(--text-faint);font-family:var(--font-mono);font-size:12px;">Not enough data.</div>'}</div>
      <div class="insight-card"><h3>Bottom Returns · ${periodShort}</h3>${bottom5.length?bottom5.map(a=>rowHtml(a)).join(''):'<div style="color:var(--text-faint);font-family:var(--font-mono);font-size:12px;">Not enough data.</div>'}</div>
      <div class="insight-card"><h3>Sector scoreboard · avg return</h3>${sectorBarsHtml}</div>
      <div class="insight-card"><h3>Idea rotation (most idea changes)</h3>${rotators.length?rotators.map(a=>churnRowHtml(a)).join(''):'<div style="color:var(--text-faint);font-family:var(--font-mono);font-size:12px;">Not enough data.</div>'}</div>
      <div class="insight-card"><h3>Highest conviction (fewest idea changes)</h3>${loyalists.length?loyalists.map(a=>churnRowHtml(a)).join(''):'<div style="color:var(--text-faint);font-family:var(--font-mono);font-size:12px;">Not enough data.</div>'}</div>
      <div class="insight-card"><h3>Crowded trades · picked by 2+ analysts</h3><div style="padding-top:2px;">${crowdedHtml}</div></div>
      <div class="insight-card wide">
        <h3>Positive momentum — <span id="momentum-count">0</span> analysts on a streak</h3>
        <div class="momentum-control">
          <input type="range" min="1" max="6" value="3" step="1" id="momentum-slider" class="momentum-slider"/>
          <span class="momentum-value"><b id="momentum-label">3 months</b> straight of positive returns, most recent reports first — independent of the period filter above</span>
        </div>
        <div id="momentum-list"></div>
      </div>
    </div>
  `;

  const slider = document.getElementById('momentum-slider');
  if(slider){
    slider.addEventListener('input', ()=> updateMomentumCard(parseInt(slider.value,10)));
    updateMomentumCard(parseInt(slider.value,10));
  }
}

document.getElementById('search').addEventListener('input', (e)=>{
  searchTerm = e.target.value.trim();
  render();
});
document.getElementById('sortSelect').addEventListener('change', (e)=>{
  sortMode = e.target.value;
  render();
});

document.getElementById('stat-analysts').textContent = DATA.length;
document.getElementById('stat-picks').textContent = DATA.reduce((s,a)=>s+a.history.length,0).toLocaleString();
buildMarquee();
buildTabs();
buildTimeTabs();
buildPageTabs();
render();
