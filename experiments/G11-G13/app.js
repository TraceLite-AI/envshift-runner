'use strict';
const $=id=>document.getElementById(id), E=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
let state, selectedVendor, pendingSearch=false, activeResult=-1, matchedVendors=[], draftChanges=new Map();
async function send(action){const r=await fetch('/api/action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(action)});const d=await r.json();if(!r.ok)throw Error(d.error);state=d;}
function message(t){$('message').textContent=t;}
function render(){if(TASK==='G11')report();else if(TASK==='G12')order();else grid();}
function report(){
 $('app').innerHTML=`<h1>Approved revenue report</h1><p>September 2026 · Revision <b>${state.revision}</b></p><table><tr><th>Account</th><th>Amount EUR</th></tr>${state.rows.map(r=>`<tr><td>${r.account}</td><td>${r.amount}</td></tr>`).join('')}</table><p>Save as <b>revenue-2026-09.csv</b> in Downloads. Replace the stale September file. Keep the August file unchanged.</p><button id="export" onclick="exportReport()">Export approved CSV…</button><p class="muted">The export opens your system's Save dialog.</p><div id="saved">${state.exports.length?'Last saved: '+E(state.exports.at(-1).name):'No export saved yet.'}</div>`;
 if(!window.showSaveFilePicker){$('export').disabled=true;message('This browser does not support the required Save dialog.');}
}
async function exportReport(){
 try{
  // Invoke immediately during activation. No awaited work before the picker.
  const handle=await window.showSaveFilePicker({suggestedName:'revenue-2026-09.csv',startIn:'downloads',types:[{description:'CSV report',accept:{'text/csv':['.csv']}}]});
  const r=await fetch('/report.csv');if(!r.ok)throw Error('Report unavailable');const bytes=await r.arrayBuffer();
  const stream=await handle.createWritable();await stream.write(bytes);await stream.close();
  await send({op:'export',name:handle.name});report();message('Report saved: '+handle.name);
 }catch(e){message(e.name==='AbortError'?'Export cancelled.':e.message);}
}
function vendorLabel(id){const v=state.vendors.find(v=>v.id===id);return `${v.name} · ${v.id} · ${v.city}`;}
function order(){
 selectedVendor=state.orders[0].vendor_id;pendingSearch=false;
 $('app').innerHTML=`<h1>Purchase order PO-918</h1><p>Amount: EUR ${state.orders[0].amount} · Reference: ${state.orders[0].reference}</p><p>Requested supplier: <b>Cedar Components · VEN-1048 · Rotterdam</b></p><label for="vendor-query">Supplier</label><div class="combobox"><input id="vendor-query" role="combobox" aria-autocomplete="list" aria-controls="vendor-results" aria-expanded="false" autocomplete="off" value="${E(vendorLabel(selectedVendor))}" onfocus="showVendors('')" oninput="searchVendor(this.value)" onkeydown="vendorKey(event)"><div id="vendor-results" role="listbox" hidden></div></div><p id="selected-vendor" class="notice"></p><p class="muted">Type to search, then choose a result to select that supplier. Escape cancels the search.</p><button id="save-order" onclick="saveOrder()">Save purchase order</button><h2>Other purchase order</h2><p>PO-919 · Cedar Components · VEN-1084 · EUR 392.50</p>`;
 updateVendorStatus();
}
function updateVendorStatus(){$('selected-vendor').textContent='Selected supplier: '+vendorLabel(selectedVendor)+(pendingSearch?' — search pending':'');$('save-order').disabled=pendingSearch;}
function showVendors(q){
 activeResult=-1;matchedVendors=state.vendors.filter(v=>(v.name+' '+v.id+' '+v.city).toLowerCase().includes(q.toLowerCase()));
 $('vendor-query').setAttribute('aria-expanded','true');$('vendor-results').hidden=false;
 $('vendor-results').innerHTML=matchedVendors.map(v=>`<button type="button" role="option" aria-selected="false" id="vendor-${v.id}" onclick="pickVendor('${v.id}')">${E(vendorLabel(v.id))}</button>`).join('')||'<p>No matching suppliers</p>';
}
function searchVendor(q){pendingSearch=true;showVendors(q);updateVendorStatus();}
function closeVendors(){$('vendor-results').hidden=true;$('vendor-query').setAttribute('aria-expanded','false');$('vendor-query').removeAttribute('aria-activedescendant');}
function pickVendor(id){selectedVendor=id;pendingSearch=false;$('vendor-query').value=vendorLabel(id);closeVendors();updateVendorStatus();$('save-order').focus();}
function vendorKey(e){
 if(e.key==='Escape'){e.preventDefault();pendingSearch=false;$('vendor-query').value=vendorLabel(selectedVendor);closeVendors();updateVendorStatus();}
 if(e.key==='ArrowDown'||e.key==='ArrowUp'){
  e.preventDefault();if($('vendor-results').hidden)showVendors('');if(!matchedVendors.length)return;
  activeResult=(activeResult+(e.key==='ArrowDown'?1:matchedVendors.length-1)+matchedVendors.length)%matchedVendors.length;
  matchedVendors.forEach((v,i)=>$('vendor-'+v.id).setAttribute('aria-selected',String(i===activeResult)));
  $('vendor-query').setAttribute('aria-activedescendant','vendor-'+matchedVendors[activeResult].id);
 }
 if(e.key==='Enter'&&activeResult>=0&&!$('vendor-results').hidden){e.preventDefault();pickVendor(matchedVendors[activeResult].id);}
}
async function saveOrder(){try{await send({op:'save-order',id:'PO-918',vendor_id:selectedVendor});order();message('Saved PO-918 with '+vendorLabel(selectedVendor));}catch(e){message(e.message);}}
const cols=[['sku','SKU'],['name','Product'],['warehouse','Warehouse'],['category','Category'],['bin','Bin'],['on_hand','On hand'],['reserved','Reserved'],['incoming','Incoming'],['lead_days','Lead days'],['unit_cost','Unit cost'],['supplier','Supplier'],['pack','Pack size'],['reorder_level','Reorder level'],['reorder_quantity','Reorder quantity']];
function grid(){
 draftChanges.clear();$('app').innerHTML='<h1>Inventory planning</h1><p>Update Reorder level: <b>SKU-1048 → 24; SKU-1084 → 36; SKU-1148 → 18.</b> Keep all other cells unchanged.</p><p class="muted">Scroll the table horizontally to reach planning columns. SKU labels remain pinned on the left.</p><div id="grid-scroll" tabindex="0"><table class="inventory"><thead><tr>'+cols.map(([k,t])=>`<th class="${k==='sku'?'pinned':''}">${t}</th>`).join('')+'</tr></thead><tbody>'+state.rows.map(r=>'<tr>'+cols.map(([k,t])=>`<td class="${k==='sku'?'pinned':''}">${k.startsWith('reorder_')?`<input id="cell-${r.sku}-${k}" aria-label="${r.sku} ${t}" value="${r[k]}" inputmode="numeric" oninput="editCell('${r.sku}','${k}',this.value)">`:E(r[k])}</td>`).join('')+'</tr>').join('')+'</tbody></table></div><div class="save-bar"><span id="change-count">0 unsaved cells</span><button id="save-grid" onclick="saveGrid()">Save changes</button></div>';
}
function editCell(sku,field,value){const key=sku+':'+field,previous=state.rows.find(r=>r.sku===sku)[field];if(String(previous)===value)draftChanges.delete(key);else draftChanges.set(key,{sku,field,value});$('change-count').textContent=draftChanges.size+' unsaved cells';}
async function saveGrid(){
 try{const changes=[...draftChanges.values()];if(changes.some(c=>!/^\d+$/.test(c.value)))throw Error('Enter whole numbers before saving.');await send({op:'save-grid',changes:changes.map(c=>({...c,value:Number(c.value)}))});const position=$('grid-scroll').scrollLeft;grid();$('grid-scroll').scrollLeft=position;message('Inventory changes saved.');}catch(e){message(e.message);}
}
fetch('/api/state').then(r=>r.json()).then(d=>{state=d;render();}).catch(e=>message(e.message));
