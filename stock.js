// stock.js
document.addEventListener('DOMContentLoaded', () => {
  const el = id => document.getElementById(id);
  const formatTime = d => new Date(d).toLocaleTimeString();

  let liveChart, chartData;
  function initChart() {
    const ctx = el('liveChart').getContext('2d');
    chartData = { labels: [], datasets: [{ label:'Price', data:[], tension:0.25, pointRadius:0, borderWidth:2, fill:true, backgroundColor:'rgba(2,200,245,0.08)', borderColor:'rgba(2,200,245,0.9)'}] };
    liveChart = new Chart(ctx,{type:'line',data:chartData,options:{responsive:true,plugins:{legend:{display:false}},scales:{x:{display:true},y:{display:true}}}});
  }

  let simTimer=null;
  function startSim(ms=1000){
    stopSim();
    simTimer=setInterval(()=>{
      const last=chartData.datasets[0].data.slice(-1)[0]??150;
      const next=+(last*(1+(Math.random()-0.48)/200)).toFixed(2);
      chartData.labels.push(formatTime(Date.now()));
      chartData.datasets[0].data.push(next);
      if(chartData.labels.length>60){chartData.labels.shift();chartData.datasets[0].data.shift()}
      liveChart.update('none');
      el('stat-price').textContent='$'+next;
      const change=(next-(chartData.datasets[0].data[0]||next)).toFixed(2);
      el('stat-change').textContent=(change>0?'+':'')+change;
      el('stat-vol').textContent=(Math.floor(Math.random()*9000)+100).toLocaleString();
      el('last-updated').textContent=formatTime(Date.now());
    },ms);
  }
  function stopSim(){if(simTimer){clearInterval(simTimer);simTimer=null}}

  // Watchlist
  const WATCH_KEY='stockit_watchlist_v1';
  const loadWatch=()=>{try{const raw=localStorage.getItem(WATCH_KEY);return raw?JSON.parse(raw):[]}catch(e){return[]}};
  const saveWatch=list=>localStorage.setItem(WATCH_KEY,JSON.stringify(list));
  function renderWatch(){
    const ul=el('watch-ul'); ul.innerHTML='';
    const list=loadWatch();
    if(list.length===0){ul.innerHTML='<div style="color:var(--muted);padding:8px">No tickers yet.</div>';return}
    list.forEach(t=>{
      const li=document.createElement('li');
      li.innerHTML=`<div style="font-weight:700">${t}</div><div style="opacity:0.8">-- $</div>`;
      const rm=document.createElement('button');rm.textContent='Remove';rm.className='input';rm.style.marginLeft='8px';
      rm.onclick=()=>{saveWatch(loadWatch().filter(x=>x!==t));renderWatch()};
      li.appendChild(rm);ul.appendChild(li);
    });
  }

  // News
  async function fetchNews(){
    const list=el('news-list'); list.innerHTML='<div style="color:var(--muted)">Loading news...</div>';
    try{
      await new Promise(r=>setTimeout(r,500));
      const items=[{title:'Markets drift higher as earnings season begins',time:'1h'},{title:'Tech leads gains; chipmakers rally',time:'2h'},{title:'Economists watch inflation data closely',time:'4h'}];
      list.innerHTML='';
      items.forEach(it=>{
        const d=document.createElement('div');d.className='news-item';
        d.innerHTML=`<strong>${it.title}</strong><div style="font-size:12px;color:var(--muted);margin-top:6px">${it.time} ago — quick summary</div>`;
        list.appendChild(d);
      });
    }catch(e){list.innerHTML='<div style="color:var(--muted)">Failed to load news.</div>'}
  }

  // Init
  initChart(); renderWatch(); fetchNews(); startSim(1000);

  el('add-btn').onclick=()=>{const val=el('ticker-input').value.trim().toUpperCase();if(!val)return;const list=loadWatch();if(!list.includes(val)){list.push(val);saveWatch(list);renderWatch();}el('ticker-input').value='';};
  el('clear-btn').onclick=()=>{if(confirm('Clear watchlist?')){saveWatch([]);renderWatch();}};
  el('populate-btn').onclick=()=>{saveWatch(['AAPL','TSLA','GOOG','MSFT']);renderWatch();};
  el('refresh-news').onclick=fetchNews;
  el('start').onclick=()=>{const iv=parseInt(el('interval').value.replace('s',''))||1;startSim(iv*1000)};
  el('stop').onclick=stopSim;
});
