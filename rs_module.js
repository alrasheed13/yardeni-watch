/* Druckenmiller-inspired relative-strength visualization, local endpoints only. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const S = ['XHB','XRT','IYT'];
  const COLORS = {XHB:'#3b82f6',XRT:'#ef5b66',IYT:'#21a675'};
  const LABELS = {XHB:'Housing',XRT:'Retail',IYT:'Transportation'};
  let current=null, busy=false, triedAuto=false;
  function modeLang(){return (typeof LANG!=='undefined' && LANG==='ar')?'ar':'en'}
  function msg(en,ar){return modeLang()==='ar'?ar:en}
  function text(id,v){let el=$(id);if(el)el.textContent=v}
  const n=(x,d=3)=>typeof x==='number' && Number.isFinite(x)?x.toFixed(d):'—';
  function rsInfo(s){return current?.data?.sectors?.[s]}
  function setError(message){text('rsError',message||'');$('rsError').style.display=message?'block':'none'}
  function sourceLabel(r){
    let status=r?.status||'missing';
    let verified=status==='fresh';
    text('rsDataStatus',status.toUpperCase());$('rsDataStatus').className='rs-pill '+(verified?'rs-badge-fresh':status==='stale'?'rs-badge-stale':'rs-badge-missing');
    text('rsDataSource',`${msg('Source','المصدر')}: ${r?.source||'—'} · ${r?.price_basis||''} · ${msg('As of','بتاريخ')}: ${r?.asof||'—'} · ${status.toUpperCase()}`);
  }
  function parseResponse(r){
    if(!r.ok)throw Error(r.error||'Unable to load data');
    current=r;setError('');sourceLabel(r);draw();
  }
  async function getCurrent(){
    if(busy)return;
    const args=new URLSearchParams({base:$('rsBase').value,ma_len:$('rsEma').value});
    try{const res=await fetch('/api/rs?'+args,{cache:'no-store'});const j=await res.json();parseResponse(j)}
    catch(e){sourceLabel({status:'missing'});setError(e.message);resetStats();if(!triedAuto&&['127.0.0.1','localhost'].includes(location.hostname)){triedAuto=true;refresh();}}
  }
  async function refresh(){
    if(busy)return;busy=true;$('rsRefresh').disabled=true;setError('');text('rsActionNote',msg('Fetching adjusted end-of-day ETF history...','جلب أسعار الإغلاق المعدلة...'));
    try{
      const resp=await fetch('/api/rs/refresh',{method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({base:$('rsBase').value,ma_len:+$('rsEma').value})});
      parseResponse(await resp.json());
      if(!resp.ok)throw Error('HTTP '+resp.status);
      text('rsActionNote',msg('History refreshed from the source.','تم تحديث السجل من المصدر.'));
    }catch(e){setError(e.message);text('rsActionNote',msg('Refresh failed; existing cached data was not overwritten.','فشل التحديث؛ لم نستبدل السجل المحفوظ.'))}
    finally{busy=false;$('rsRefresh').disabled=false}
  }
  function validCSV(textData){
    const lines=textData.replace(/^\uFEFF/,'').trim().split(/\r?\n/).filter(x=>x.trim());
    if(lines.length<64)throw Error('CSV needs at least 63 dated rows plus a header.');
    if(lines.length>5001)throw Error('CSV too long');
    const keys=lines[0].split(',').map(x=>x.trim().toUpperCase());
    for(let col of ['DATE','SPY','XHB','XRT','IYT'])if(!keys.includes(col))throw Error('CSV missing column '+col);
    const output=[];
    for(const [i,line] of lines.slice(1).entries()){
      const vals=line.split(',').map(x=>x.trim());
      let row={date:vals[keys.indexOf('DATE')]};
      for(const col of ['SPY','XHB','XRT','IYT','QQQ','IWM']){
        const idx=keys.indexOf(col);if(idx!==-1&&vals[idx]!=='')row[col]=+vals[idx];
      }
      output.push(row);
    }
    return output;
  }
  async function importCSV(file){
    if(!file)return;
    busy=true;setError('');text('rsActionNote',msg('Validating local CSV...','التحقق من CSV المحلي...'));
    try{
      const content=await file.text();const rows=validCSV(content);
      const resp=await fetch('/api/rs/import',{method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({rows,base:$('rsBase').value,ma_len:+$('rsEma').value,
          price_basis:'user-supplied daily close values, adjustments unspecified'})});
      const result=await resp.json();parseResponse(result);
      text('rsActionNote',msg('CSV imported; provenance marked unverified.','تم استيراد CSV مع تمييز مصدره كبيانات لم تتحقق خارجيًا.'));
    }catch(e){setError(e.message);text('rsActionNote','')}
    finally{busy=false;$('rsImport').value=''}
  }
  function resetStats(){
    for(const s of S){text('rs-'+s+'-signal','Not available');text('rs-'+s+'-ratio','—');text('rs-'+s+'-perf','—');
      const sv=$('rs-'+s+'-svg');if(sv)sv.innerHTML='';}
    text('rsWeakCount','—');text('rsLeadCount','—');text('rsAsOf','—');
    text('rsDiagnosis',msg('Import a dated CSV or refresh ETF history to calculate signals.','ارفع CSV مؤرخًا أو حدّث أسعار الصناديق لحساب الإشارات.'));
    $('rsCombinedChart').innerHTML='';
  }
  function svgEl(name, attrs={}){
    const e=document.createElementNS('http://www.w3.org/2000/svg',name);
    for(let k in attrs)e.setAttribute(k,attrs[k]);return e;
  }
  function drawChart(svg, series, dates, {showEma=true, mini=false, benchmark=false}={}){
    svg.innerHTML='';const W=mini?500:1060,H=mini?180:280;
    const left=mini?42:54,right=12,top=16,bottom=mini?26:34;
    svg.setAttribute('viewBox',`0 0 ${W} ${H}`);
    svg.setAttribute('role','img');
    svg.setAttribute('aria-label',mini?'Daily ETF/SPY raw ratio and EMA':'Normalized RS values by ETF relative to benchmark');
    const vals=series.flatMap(s=>s.values.filter(v=>typeof v==='number'&&Number.isFinite(v)));
    if(vals.length===0)return;
    let lo=Math.min(...vals),hi=Math.max(...vals);if(hi===lo){hi*=1.01;lo*=.99}
    const pad=(hi-lo)*.10;hi+=pad;lo-=pad;
    const X=i=>left+(W-left-right)*(i/Math.max(1,dates.length-1));
    const Y=v=>top+(H-top-bottom)*(1-(v-lo)/(hi-lo));
    const makePath=(values)=>{
      let parts=[],active=false;
      for(let i=0;i<values.length;i++){
        let v=values[i];if(v===null||!Number.isFinite(v)){active=false;continue}
        parts.push(`${active?'L':'M'}${X(i).toFixed(2)},${Y(v).toFixed(2)}`);active=true;
      }
      return parts.join(' ');
    };
    const g=svgEl('g');svg.appendChild(g);
    for(let z=0;z<4;z++){
      const y=top+(H-top-bottom)*z/3;
      g.appendChild(svgEl('line',{x1:left,y1:y,x2:W-right,y2:y,stroke:'currentColor','stroke-opacity':'.12'}));
      const lab=svgEl('text',{x:left-8,y:y+4,'text-anchor':'end','font-size':'11',fill:'currentColor',opacity:'.65'});
      lab.textContent=mini?(hi-(hi-lo)*z/3).toFixed(3):(hi-(hi-lo)*z/3).toFixed(1);g.appendChild(lab);
    }
    if(benchmark&&100>lo&&100<hi){g.appendChild(svgEl('line',{x1:left,y1:Y(100),x2:W-right,y2:Y(100),stroke:'currentColor','stroke-opacity':'.30','stroke-dasharray':'5 5'}))}
    const first=svgEl('text',{x:left,y:H-7,'font-size':'11',fill:'currentColor',opacity:'.6'});first.textContent=dates[0]||'';g.appendChild(first);
    const last=svgEl('text',{x:W-right,y:H-7,'text-anchor':'end','font-size':'11',fill:'currentColor',opacity:'.6'});last.textContent=dates[dates.length-1]||'';g.appendChild(last);
    for(const line of series){if(line.ema && !showEma)continue;g.appendChild(svgEl('path',{d:makePath(line.values),fill:'none',stroke:line.color,'stroke-width':line.ema?'1.5':(mini?'2.7':'3'),
      'stroke-dasharray':line.ema?'4 5':'none',opacity:line.ema?.65:1,'stroke-linecap':'round','stroke-linejoin':'round'}));}
    let tt=svgEl('g',{style:'display:none;pointer-events:none'});let cursor=svgEl('line',{x1:left,y1:top,x2:left,y2:H-bottom,stroke:'currentColor','stroke-opacity':'.5','stroke-dasharray':'3 3'});tt.appendChild(cursor);
    let rect=svgEl('rect',{x:left,y:2,width:mini?180:300,height:18,rx:4,fill:'#17233e',opacity:'.92'});tt.appendChild(rect);
    let tip=svgEl('text',{x:left+7,y:15,fill:'#fff','font-size':'10'});tt.appendChild(tip);svg.appendChild(tt);
    svg.onmousemove=(ev)=>{
      const bounds=svg.getBoundingClientRect();const mouseX=(ev.clientX-bounds.left)*(W/bounds.width);
      const i=Math.max(0,Math.min(dates.length-1,Math.round((mouseX-left)/(W-left-right)*(dates.length-1))));
      const x=X(i);cursor.setAttribute('x1',x);cursor.setAttribute('x2',x);
      rect.setAttribute('x',Math.min(W-(mini?190:320),Math.max(left,x+8)));
      tip.setAttribute('x',Math.min(W-(mini?183:313),Math.max(left+7,x+15)));
      tip.textContent=(dates[i]||'')+' · '+series.filter(s=>!s.ema).map(s=>s.label+' '+n(s.values[i],mini?4:1)).join(' · ');
      tt.style.display='';
    };
    svg.onmouseleave=()=>tt.style.display='none';
  }
  function draw(){
    if(!current?.ok)return resetStats();
    const d=current.data; const count=$('rsPeriod').value;const windowLen=count==='all'?10000:parseInt(count,10);
    const color=(sig)=>sig==='Leading'?'leading':sig==='Weakening'?'weakening':sig==='Improving'?'improving':'mixed';
    text('rsWeakCount',d.fresh?(d.weak_count+'/3'):'N/A');text('rsLeadCount',d.fresh?(d.lead_count+'/3'):'N/A');text('rsAsOf',d.asof);
    text('rsDiagnosis',d.diagnosis);
    for(const sym of S){
      const sector=d.sectors[sym],p=sector.points.slice(-windowLen),dates=p.map(x=>x.date);
      text('rs-'+sym+'-ratio',n(sector.ratio,4));
      const sign=sector.rs_change20_pct>=0?'+':'';
      text('rs-'+sym+'-perf',sign+n(sector.rs_change20_pct,2)+'%');
      text('rs-'+sym+'-signal',sector.signal);
      $('rs-'+sym+'-signal').className='rs-pill '+color(sector.signal);
      const seq=[{label:'RS',color:COLORS[sym],values:p.map(x=>x.ratio)},
        {label:'EMA'+d.ma_len,color:COLORS[sym],values:p.map(x=>x.ema),ema:true}];
      drawChart($('rs-'+sym+'-svg'),seq,dates,{mini:true,showEma:$('rsShowEMA').checked});
    }
    const all=S.map(sym=>d.sectors[sym].points.slice(-windowLen));
    const dates=all[0].map(x=>x.date);
    const lines=S.map((sym,i)=>{
      const p=all[i];const origin=p[0].ratio;
      return {label:sym,color:COLORS[sym],values:p.map(x=>100*x.ratio/origin)};
    });
    drawChart($('rsCombinedChart'),lines,dates,{benchmark:true});
    text('rsBaselineLabel',d.base);text('rsEMALabel','EMA '+d.ma_len);
  }
  window.applyRSLanguage=()=>{
    text('rsSectionTitle',msg('Druckenmiller Economic Indicator','مؤشر دراكنميلر الاقتصادي'));
    text('rsDescription',msg('Economic-sensitive ETF relative strength versus a market baseline. Signals based on completed daily closes; independent of the Yardeni score.',
      'القوة النسبية لقطاعات حساسة للاقتصاد مقابل مؤشر مرجعي، من إغلاقات يومية مكتملة. الإشارات مستقلة عن درجة Yardeni.'));
    text('rsMethodNotice',msg('A ratio below its EMA reflects relative underperformance, not proof of institutional distribution. XHB includes homebuilding-related suppliers; IYT includes airlines and rail, not only freight.',
      'هبوط النسبة تحت متوسطها يدل على ضعف الأداء النسبي، وليس دليلًا مباشرًا على خروج المؤسسات. XHB يضم مورّدين للبناء، وIYT يضم شركات طيران وسككًا حديدية، وليس الشحن فقط.'));
    text('rsImportLabel',msg('Import dated CSV','استيراد CSV مؤرخ'));
    text('rsRefreshLabel',msg('Refresh ETF history','تحديث أسعار الصناديق'));
    text('rsMainTitle',msg('Three-sector relative performance (rebased to 100)','الأداء النسبي للقطاعات الثلاثة (الأساس 100)'));
    if(current?.ok)draw();
  };
  $('rsRefresh').addEventListener('click',refresh);
  $('rsImport').addEventListener('change',e=>importCSV(e.target.files[0]));
  for(let id of ['rsBase','rsEma'])$(id).addEventListener('change',getCurrent);
  for(let id of ['rsPeriod','rsShowEMA'])$(id).addEventListener('change',draw);
  window.applyRSLanguage();
  const isLocal=['127.0.0.1','localhost'].includes(location.hostname);
  if(isLocal)getCurrent();else {resetStats();setError(msg('Use the Windows local server to load ETF history.','شغّل السيرفر المحلي على Windows لتحديث سجل الصناديق.'))}
})();
