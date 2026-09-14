let state, page='home', catalogPage=1, selectedProduct=null, selectedReport=null, notice='', isError=false;
let selected=new Set(), query='', canonicalChoice='';
const app=document.getElementById('app');
const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const button=(id,text,extra='')=>`<button id="${id}" ${extra}>${text}</button>`;
async function post(a){const r=await fetch('/api/action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(a)});const d=await r.json();if(!r.ok)throw Error(d.error);state=d;return d;}
function bind(id,fn){const e=document.getElementById(id);if(e)e.addEventListener('click',async()=>{try{isError=false;await fn();}catch(err){notice=err.message;isError=true;render();}});}
function go(p){page=p;notice='';isError=false;render();window.scrollTo(0,0);}
function nav(items){document.getElementById('nav').innerHTML=items.map(([p,t])=>button('nav-'+p,t,`class="${page===p?'active':''}"`)).join('');items.forEach(([p])=>bind('nav-'+p,()=>go(p)));}
function message(){return notice?`<div role="status" class="notice ${isError?'error':''}">${esc(notice)}</div>`:'';}
function policy(){return `<details class="panel policy"><summary>REQ-204 · Replenishment policy (available on every page)</summary><p>${esc(state.requests[0].policy)}</p></details>`;}
function renderSupply(){
  nav([['home','Requests'],['inventory','Inventory'],['catalog','Catalog'],['cart',`Cart (${Object.keys(state.cart).length})`],['orders','Orders']]);
  let html='<h1>Supply Desk</h1>'+policy()+message();
  if(page==='home'){
    html+='<h2>Replenishment requests</h2>'+state.requests.map(r=>`<section><div class="row between"><h3>${r.id} · ${r.title}</h3><span class="badge">${r.status}</span></div><p>${esc(r.policy)}</p>${r.order_id?`<p class="badgelink">Linked order: ${r.order_id}</p>`:''}${r.id==='REQ-204'&&r.status==='Open'?`<label>Submitted order <select id="request-order"><option value="">Select order…</option>${state.orders.map(o=>`<option value="${o.id}">${o.id} · ${esc(o.reference)} · ${o.destination}</option>`).join('')}</select></label>${button('resolve-request','Resolve request',{toString:()=>state.orders.length?'class="primary"':'disabled'})}`:''}</section>`).join('');
  } else if(page==='inventory'){
    html+='<h2>North Lab inventory</h2><p>All quantities below are individual units. Catalog quantities are packs.</p><div class="tablewrap"><table><thead><tr><th>Product</th><th>On hand</th><th>Reserved</th><th>Incoming</th><th>Minimum</th><th>Target</th><th>Units / pack</th></tr></thead><tbody>'+state.inventory.map(p=>`<tr><td><b>${p.id}</b><br>${p.name}</td>${['on_hand','reserved','incoming','minimum','target','pack_size'].map(k=>`<td>${p[k]}</td>`).join('')}</tr>`).join('')+'</tbody></table></div>';
  } else if(page==='catalog'){
    html+='<h2>Supply catalog</h2><p>Set the total number of packs for each product, then add or update it in your cart.</p><div class="cards">'+state.inventory.map(p=>`<article class="card"><h3>${p.name}</h3><p><b>${p.id}</b><br>${p.pack_size} units / pack · $${p.pack_price} / pack</p><label>Packs <input id="qty-${p.id}" type="number" min="0" max="100" value="${state.cart[p.id]??1}"></label>${button('add-'+p.id,state.cart[p.id]?'Update cart':'Add to cart','class="primary"')}</article>`).join('')+'</div>';
  } else if(page==='cart'){
    html+='<h2>Purchase order cart</h2>';
    if(!Object.keys(state.cart).length)html+='<p class="empty">Your cart is empty. Submitted orders are available on the Orders page.</p>';
    else{
      html+='<section><table><thead><tr><th>Product</th><th>Units / pack</th><th>Packs</th><th>Line total</th><th></th></tr></thead><tbody>'+Object.entries(state.cart).map(([id,q])=>{const p=state.inventory.find(x=>x.id===id);return `<tr><td>${id}<br>${p.name}</td><td>${p.pack_size}</td><td><input id="cartqty-${id}" type="number" value="${q}" min="0" max="100"></td><td>$${p.pack_price*q}</td><td>${button('update-'+id,'Update')}</td></tr>`;}).join('')+'</tbody></table>';
      html+='<label>Delivery <select id="destination"><option>North Lab</option><option>South Lab</option></select></label><label>Priority <select id="priority"><option>Standard</option><option>Urgent</option></select></label><label>Reference <input id="order-reference" placeholder="Request ID"></label>'+button('submit-order','Submit purchase order','class="primary"')+'</section>';
    }
  } else if(page==='orders'){
    html+='<h2>Submitted purchase orders</h2>'+(state.orders.length?state.orders.map(o=>`<section><h3>${o.id} · ${esc(o.reference)}</h3><p>${o.destination} · ${o.priority}</p><table><thead><tr><th>Product</th><th>Packs</th><th>Units</th></tr></thead><tbody>${Object.entries(o.items).map(([id,q])=>`<tr><td>${id}</td><td>${q}</td><td>${q*state.inventory.find(p=>p.id===id).pack_size}</td></tr>`).join('')}</tbody></table><p>Order submitted successfully. Return to Requests to link this order.</p></section>`).join(''):'<p>No orders submitted.</p>');
  }
  app.innerHTML=html;
  for(const p of state.inventory){
    bind('add-'+p.id,async()=>{await post({op:'cart',product:p.id,quantity:Number(document.getElementById('qty-'+p.id).value)});notice='Cart updated: '+p.id+' · '+(state.cart[p.id]??0)+' packs';render();});
    bind('update-'+p.id,async()=>{await post({op:'cart',product:p.id,quantity:Number(document.getElementById('cartqty-'+p.id).value)});notice='Cart updated';render();});
  }
  bind('submit-order',async()=>{await post({op:'submit-order',destination:document.getElementById('destination').value,priority:document.getElementById('priority').value,reference:document.getElementById('order-reference').value});page='orders';notice='Purchase order '+state.orders.at(-1).id+' submitted';render();window.scrollTo(0,0);});
  bind('resolve-request',async()=>{await post({op:'resolve-request',id:'REQ-204',order_id:document.getElementById('request-order').value});notice='REQ-204 resolved and linked to '+state.requests[0].order_id;render();});
}
// Original SVG art. Distinguishing features are visible shapes and their arrangement, never text labels.
function tote(i){
  const configs=[
    [0,0,0],[1,1,0],[0,2,1],[2,0,1],[1,2,2],[2,1,0],
    [0,1,2],[1,0,2],[2,2,1],[2,0,2],[1,2,0],[0,2,2],
  ];
  const [shape,layout,band]=configs[i];const coral='#c95e48',navy='#234c60',gold='#cf9b31';
  const shapes=[`<circle cx="${layout===2?110:layout===1?80:52}" cy="${layout===1?87:72}" r="18" fill="${coral}"/>`,
    `<path d="M ${layout===2?92:42} 91 l 18 -35 l 18 35 Z" fill="${coral}"/>`,
    `<rect x="${layout===2?93:layout===1?62:34}" y="${layout===1?81:55}" width="34" height="34" rx="3" fill="${coral}"/>`];
  const bands=[`<path d="M35 118H125 M35 129H125" stroke="${navy}" stroke-width="7"/>`,
    `<path d="M40 100L95 145 M58 95L115 141" stroke="${navy}" stroke-width="8"/>`,
    `<path d="M45 101V145 M59 101V145" stroke="${navy}" stroke-width="8"/>`];
  return `<svg viewBox="0 0 160 180" role="img" aria-label="Tote product photograph illustration"><rect width="160" height="180" rx="8" fill="#f0eee8"/><ellipse cx="80" cy="160" rx="59" ry="8" fill="#d8d6d0"/><path d="M56 48V30a24 24 0 0 1 48 0v18" fill="none" stroke="#776952" stroke-width="8"/><path d="M31 45H129L139 157H21Z" fill="#ece0bd" stroke="#8d7b5b" stroke-width="2"/><path d="M32 49H128" stroke="#c0ad84" stroke-width="3"/>${shapes[shape]}${bands[band]}<circle cx="${layout===2?51:111}" cy="${layout===1?65:83}" r="8" fill="${gold}"/></svg>`;
}
function reference(){return `<aside class="reference"><h2>Reference image</h2>${tote(8)}<p class="muted">Match the printed design. Required variant: 18 L, Zipper. Quantity: 2.</p></aside>`;}
function renderShop(){
  nav([['home','Shop'],['cart',`Cart (${state.cart.reduce((n,r)=>n+r.quantity,0)})`]]);
  let html='<h1>Field Goods</h1>'+message();
  if(page==='home'){
    html+=`<div class="shopping">${reference()}<div><div class="row between"><h2>Trail tote collection</h2><span class="muted">12 designs · Page ${catalogPage} of 2</span></div><div class="cards">`+state.products.slice((catalogPage-1)*6,catalogPage*6).map(p=>`<article class="card">${tote(p.print)}<h3>${p.name}</h3><p class="compact">Style ${p.id} · $${p.price}</p>${button('product-'+p.id,'View options')}</article>`).join('')+`</div><div class="pagination">${button('previous','Previous',catalogPage===1?'disabled':'')}${button('next','Next',catalogPage===2?'disabled':'')}</div></div></div>`;
  } else if(page==='product'){
    const p=state.products.find(p=>p.id===selectedProduct);
    html+=`<div class="shopping">${reference()}<section><div class="detail"><div>${tote(p.print)}</div><div><h2>${p.name}</h2><p>Style ${p.id} · $${p.price}</p><label>Size <select id="size"><option>12 L</option><option>18 L</option><option>24 L</option></select></label><label>Closure <select id="closure"><option>Open</option><option>Zipper</option></select></label><label>Quantity <input type="number" min="1" max="20" id="quantity" value="1"></label>${button('add-tote','Add to cart','class="primary"')}<p>${button('back-collection','Back to collection')}</p></div></div></section></div>`;
  } else if(page==='cart'){
    html+=`<div class="shopping">${reference()}<section><h2>Your cart</h2>`+state.cart.map((r,i)=>`<div class="row" style="border-bottom:1px solid #ccd9df;padding:12px 0"><div style="width:110px">${r.product==='POUCH-01'?'<div style="height:90px;background:#aec1b7;border-radius:15px;padding:20px;font-size:14px">Travel pouch</div>':tote(state.products.find(p=>p.id===r.product).print)}</div><div><h3>${r.name} · ${r.product}</h3><p>${r.size} · ${r.closure}</p><label>Quantity <input id="cartqty-${i}" type="number" value="${r.quantity}" min="0" max="20">${button('update-'+i,'Update')}${button('remove-'+i,'Remove')}</label></div></div>`).join('')+'<p class="muted">Cart contents are saved automatically when you add or update an item.</p></section></div>';
  }
  app.innerHTML=html;
  bind('next',()=>{catalogPage=2;render();window.scrollTo(0,0);});bind('previous',()=>{catalogPage=1;render();window.scrollTo(0,0);});
  state.products.forEach(p=>bind('product-'+p.id,()=>{selectedProduct=p.id;go('product');}));
  bind('back-collection',()=>go('home'));
  bind('add-tote',async()=>{await post({op:'add-cart',product:selectedProduct,size:document.getElementById('size').value,closure:document.getElementById('closure').value,quantity:Number(document.getElementById('quantity').value)});page='cart';notice='Added to cart';render();window.scrollTo(0,0);});
  state.cart.forEach((r,i)=>{bind('update-'+i,async()=>{await post({op:'set-cart',index:i,quantity:Number(document.getElementById('cartqty-'+i).value)});notice='Cart updated';render();});bind('remove-'+i,async()=>{await post({op:'set-cart',index:i,quantity:0});notice='Item removed';render();});});
}
function bulk(){return `<div class="bulk"><div class="row"><b>${selected.size} selected</b><label>Canonical report <select id="canonical"><option value="">Select report…</option>${state.reports.filter(r=>r.status==='Open').map(r=>`<option value="${r.id}">${r.id}</option>`).join('')}</select></label>${button('resolve-duplicates','Resolve selected as Duplicate','class="primary"')}${button('clear-selection','Clear selection')}</div><div class="muted">The selected reports will be resolved and linked to the canonical report. The canonical report must not be selected.</div></div>`;}
function reportTable(rows,compare=false){return `<div class="tablewrap"><table class="${compare?'compare':''}"><thead><tr><th>Select</th><th>Report</th><th>Customer</th>${compare?'<th>Invoice</th><th>Failure code</th>':''}<th>Created (UTC)</th><th>Status</th></tr></thead><tbody>`+rows.map(r=>`<tr><td><input id="select-${r.id}" type="checkbox" ${selected.has(r.id)?'checked':''} aria-label="Select ${r.id}"></td><td class="title">${button('report-'+r.id,r.id,'class="linkbutton"')}<br>${esc(r.title)}</td><td>${r.customer}</td>${compare?`<td>${r.invoice}</td><td>${r.failure}</td>`:''}<td>${r.created.replace(' ','<br>')}</td><td>${r.status}${r.duplicate_of?`<br>Duplicate of<br>${r.duplicate_of}`:''}</td></tr>`).join('')+'</tbody></table></div>';}
let compared=[];
function renderIncidents(){
  nav([['home','Billing API queue'],['compare','Compare reports']]);
  let html='<h1>Incident Desk</h1>'+message();
  if(page==='home'){
    const rows=state.reports.filter(r=>[r.id,r.title,r.customer].join(' ').toLowerCase().includes(query.toLowerCase()));
    html+='<h2>Billing API queue</h2><div class="row"><label>Search title / customer / ID <input id="search" value="'+esc(query)+'" placeholder="e.g. AC-72"></label>'+button('search-button','Search')+button('compare-selected','Compare selected')+button('select-all','Select visible')+'</div>'+reportTable(rows);
  } else if(page==='compare'){
    const rows=state.reports.filter(r=>compared.includes(r.id));
    html+='<h2>Compare report details</h2><p>Reports remain in this comparison when you deselect them. Select only reports to resolve; use the full details to identify the canonical report.</p>'+(rows.length?reportTable(rows,true):'<p>Select reports in the queue, then click Compare selected.</p>');
  } else if(page==='report'){
    const r=state.reports.find(r=>r.id===selectedReport);
    html+=`<section class="report-detail"><h2>${r.id} · ${esc(r.title)}</h2><dl>${['customer','invoice','failure','created','assignee','status','resolution','duplicate_of'].map(k=>`<dt>${k.replace('_',' ')}</dt><dd>${esc(r[k]??'—')}</dd>`).join('')}</dl><h3>Comments</h3>${r.comments.map(c=>`<p>${esc(c)}</p>`).join('')}${button('back-queue','Back to queue')}</section>`;
  }
  html+=bulk();app.innerHTML=html;
  const doSearch=()=>{query=document.getElementById('search').value;render();};bind('search-button',doSearch);document.getElementById('search')?.addEventListener('keydown',e=>{if(e.key==='Enter')doSearch();});
  bind('select-all',()=>{state.reports.filter(r=>[r.id,r.title,r.customer].join(' ').toLowerCase().includes(query.toLowerCase())).forEach(r=>selected.add(r.id));render();});
  bind('compare-selected',()=>{compared=[...selected];go('compare');});
  state.reports.forEach(r=>{const e=document.getElementById('select-'+r.id);e?.addEventListener('change',()=>{if(e.checked)selected.add(r.id);else selected.delete(r.id);render();});bind('report-'+r.id,()=>{selectedReport=r.id;go('report');});});
  const canonicalSelect=document.getElementById('canonical');canonicalSelect.value=canonicalChoice;canonicalSelect.addEventListener('change',()=>{canonicalChoice=canonicalSelect.value;});
  bind('back-queue',()=>go('home'));bind('clear-selection',()=>{selected.clear();render();});
  bind('resolve-duplicates',async()=>{const ids=[...selected],canonical=document.getElementById('canonical').value;await post({op:'duplicate',ids,canonical});selected.clear();notice=ids.length+' reports resolved as Duplicate of '+canonical;render();});
}
function render(){if(TASK==='G14')renderSupply();else if(TASK==='G15')renderShop();else renderIncidents();}
fetch('/api/state').then(r=>r.json()).then(s=>{state=s;render();document.documentElement.dataset.ready='true';});
