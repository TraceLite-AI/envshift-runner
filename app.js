const $=id=>document.getElementById(id),esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let state,notice='',mailTab='messages',selectedNode='launch',shareDraft=null;
const button=(id,label,attrs='')=>`<button id="${id}" ${attrs}>${label}</button>`;
const input=(id,label,value='',type='text')=>`<label>${label}<input id="${id}" type="${type}" value="${esc(value)}" autocomplete="off"></label>`;
const select=(id,label,values,value)=>`<label>${label}<select id="${id}">${values.map(v=>`<option ${v===value?'selected':''}>${esc(v)}</option>`).join('')}</select></label>`;
const check=(id,label,on=false)=>`<label class="inline"><input type="checkbox" id="${id}" ${on?'checked':''}> ${label}</label>`;
function bind(id,fn){const e=$(id);if(e)e.onclick=fn;}
async function post(action){const r=await fetch('/api/action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(action)});const data=await r.json();if(!r.ok){notice=data.error;render();return false;}state=data;notice='Changes applied';render();return true;}
function render(){
 $('app').innerHTML=`<div class="status" role="status">${esc(notice)||'Ready'}</div>`;
 ({G21:mail,G22:review,G23:workshop,G24:report,G25:sharing})[TASK]();
 document.documentElement.dataset.ready='true';
}
function mail(){
 let html=`<h1>Mailbox automation</h1><div class="toolbar">${button('tab-messages','Messages')}${button('tab-rules','Rules')}${button('new-rule','New rule')}</div>`;
 if(mailTab==='messages')html+='<table><thead><tr><th>From / subject</th><th>Attachment</th><th>Folder</th><th>Labels</th><th>Read</th></tr></thead><tbody>'+state.messages.map(m=>`<tr><td><small>${esc(m.sender)}</small><br>${esc(m.subject)}</td><td>${m.attachment?'Yes':'No'}</td><td>${m.folder}</td><td>${m.labels.map(esc).join(', ')}</td><td>${m.read?'Yes':'No'}</td></tr>`).join('')+'</tbody></table>';
 if(mailTab==='rules')html+=state.rules.map(r=>`<article class="card"><h2>${esc(r.name)}</h2><p>${r.enabled?'Enabled':'Disabled'} · Match ${r.match.toUpperCase()} · From ${esc(r.sender)} · Subject contains ${esc(r.subject)} · ${r.attachment?'Attachment required':'Any attachment status'}</p><p>Folder: ${r.folder} · Label: ${r.label} · Mark read: ${r.mark_read?'Yes':'No'}</p>${button('apply-'+r.id,'Apply to existing messages')}</article>`).join('');
 if(mailTab==='new')html+=`<section class="card"><h2>Create rule</h2><div class="formgrid">${input('rule-name','Rule name')}${select('rule-match','Match conditions',['All','Any'],'All')}${input('rule-sender','Sender equals')}${input('rule-subject','Subject contains')}</div><div class="toolbar">${check('rule-attachment','Has an attachment')}${check('rule-enabled','Enabled',true)}</div><h3>Actions</h3><div class="formgrid">${select('rule-folder','Move to folder',['Inbox','Finance','Archive'],'Inbox')}${select('rule-label','Add label',['Alert','Invoice','Follow up'],'Alert')}</div><div class="toolbar">${check('rule-read','Mark as read')}${button('save-rule','Save rule')}${button('cancel-rule','Cancel')}</div></section>`;
 $('app').insertAdjacentHTML('beforeend',html);
 bind('tab-messages',()=>{mailTab='messages';notice='';render();});bind('tab-rules',()=>{mailTab='rules';notice='';render();});bind('new-rule',()=>{mailTab='new';notice='';render();});bind('cancel-rule',()=>{mailTab='rules';render();});
 for(const r of state.rules){bind('apply-'+r.id,()=>post({op:'apply_rule',id:r.id}));const b=$('apply-'+r.id);if(b){b.insertAdjacentHTML('afterend',' '+button('delete-'+r.id,'Delete rule'));bind('delete-'+r.id,()=>post({op:'delete_rule',id:r.id}));}}
 bind('save-rule',()=>{const rule={name:$('rule-name').value,match:$('rule-match').value.toLowerCase(),sender:$('rule-sender').value,subject:$('rule-subject').value,attachment:$('rule-attachment').checked,enabled:$('rule-enabled').checked,folder:$('rule-folder').value,label:$('rule-label').value,mark_read:$('rule-read').checked};mailTab='rules';post({op:'create_rule',rule});});
}
function review(){
 let html=`<h1>${esc(state.title)}</h1><div class="toolbar">${button('save-document','Save document')}<span>${state.saved?'Document saved':'Not saved yet'} · ${state.revisions.filter(r=>r.status==='pending').length} pending revisions</span></div><div class="columns"><section><h2>Document</h2><article class="card">${state.blocks.map(b=>`<p>${esc(b.text)}</p>`).join('')}</article><h2>Comment</h2>${state.comments.map(c=>`<aside class="card"><strong>Anchor: ${esc(c.anchor)}</strong><p>${esc(c.text)}</p></aside>`).join('')}</section><section><h2>Tracked changes</h2>`;
 for(const r of state.revisions)html+=`<article class="card revision"><small>${r.id} · ${r.block} · <strong>${r.status}</strong></small><p><del>${esc(r.before)}</del><br><ins>${esc(r.after)}</ins></p><div class="toolbar">${button('accept-'+r.id,'Accept')}${button('reject-'+r.id,'Reject')}</div></article>`;
 html+='</section></div>';$('app').insertAdjacentHTML('beforeend',html);
 bind('save-document',()=>post({op:'save'}));
 for(const r of state.revisions){bind('accept-'+r.id,()=>post({op:'decide',id:r.id,decision:'accepted'}));bind('reject-'+r.id,()=>post({op:'decide',id:r.id,decision:'rejected'}));}
}
function workshop(){
 const html=`<h1>Badge source</h1><p>Crop coordinates are relative to the current image, measured from its top-left. Reset restores the original 320 × 240 source.</p><div class="columns"><section class="card"><h2>Working image</h2><img id="working-image" alt="Working image preview" src="data:image/png;base64,${state.working_png}"><p id="image-size"></p><div class="toolbar">${button('rotate-cw','Rotate clockwise')}${button('rotate-ccw','Rotate counterclockwise')}${button('reset-image','Reset to original')}</div></section><section class="card"><h2>Crop</h2><div class="formgrid">${input('crop-x','X',0,'number')}${input('crop-y','Y',0,'number')}${input('crop-width','Width',320,'number')}${input('crop-height','Height',240,'number')}</div><div class="toolbar">${button('apply-crop','Apply crop')}</div><h2>Export</h2>${select('export-format','Format',['PNG','JPEG'],'PNG')}${input('export-name','File name','image.png')}<div class="toolbar">${button('export-image','Export image')}</div></section></div><h2>Exported files</h2><ul>${Object.keys(state.exports).map(n=>`<li><a href="/export/${encodeURIComponent(n)}" download="${esc(n)}">${esc(n)}</a></li>`).join('')||'<li>No exports yet</li>'}</ul>`;
 $('app').insertAdjacentHTML('beforeend',html);
 $('working-image').onload=()=>{$('image-size').textContent=$('working-image').naturalWidth+' × '+$('working-image').naturalHeight+' pixels';};
 bind('apply-crop',()=>post({op:'crop',x:Number($('crop-x').value),y:Number($('crop-y').value),width:Number($('crop-width').value),height:Number($('crop-height').value)}));
 bind('rotate-cw',()=>post({op:'rotate',direction:'cw'}));bind('rotate-ccw',()=>post({op:'rotate',direction:'ccw'}));bind('reset-image',()=>post({op:'reset'}));
 bind('export-image',()=>post({op:'export',format:$('export-format').value,name:$('export-name').value}));
}
function series(cfg){
 const groups={};for(const r of state.rows){if(cfg.status!=='All'&&r.Status!==cfg.status)continue;(groups[r[cfg.group]]??=[]).push(r[cfg.value]);}
 return Object.entries(groups).map(([label,v])=>({label,value:cfg.aggregation==='Sum'?v.reduce((a,b)=>a+b,0):v.reduce((a,b)=>a+b,0)/v.length})).sort(cfg.sort==='Descending total'?((a,b)=>b.value-a.value||a.label.localeCompare(b.label)):((a,b)=>a.label.localeCompare(b.label)));
}
function chart(cfg){const data=series(cfg),max=Math.max(1,...data.map(x=>x.value));return `<div class="chart"><strong>${esc(cfg.title)} · ${cfg.kind}</strong>${data.map(d=>`<div class="barrow"><span>${esc(d.label)}</span><div class="bartrack"><i style="width:${d.value/max*100}%;${cfg.kind==='Line'?'height:4px;margin-top:12px':''}"></i></div><b>${Number(d.value.toFixed(2))}</b></div>`).join('')}<small>${cfg.aggregation} of ${cfg.value} · ${cfg.status} · ${cfg.sort}</small></div>`;}
function report(){
 const c=state.draft;let html=`<h1>Reports</h1><div class="columns"><section class="card"><h2>Chart settings</h2>${input('chart-title','Title',c.title)}<div class="formgrid">${select('chart-kind','Chart type',['Line','Bar'],c.kind)}${select('chart-group','Group by',['Person','Team'],c.group)}${select('chart-value','Value',['Hours'],c.value)}${select('chart-aggregation','Aggregation',['Average','Sum'],c.aggregation)}${select('chart-status','Include status',['All','Posted','Cancelled'],c.status)}${select('chart-sort','Order',['A to Z','Descending total'],c.sort)}</div><div class="toolbar">${button('apply-chart','Apply settings')}${button('save-report','Save report')}</div></section><section><h2>Applied preview</h2>${chart(c)}<h2>Saved reports</h2>${state.reports.map(r=>`<article class="card"><strong>${esc(r.title)}</strong>${r.kind==='legacy'?`<p>${esc(r.note)}</p>`:chart(r)}</article>`).join('')}</section></div><h2>Source entries</h2><table><thead><tr><th>ID</th><th>Team</th><th>Person</th><th>Hours</th><th>Status</th></tr></thead><tbody>${state.rows.map(r=>`<tr><td>${r.id}</td><td>${r.Team}</td><td>${r.Person}</td><td>${r.Hours}</td><td>${r.Status}</td></tr>`).join('')}</tbody></table>`;
 $('app').insertAdjacentHTML('beforeend',html);
 bind('apply-chart',()=>post({op:'configure',config:Object.fromEntries(['title','kind','group','value','aggregation','status','sort'].map(k=>[k,$('chart-'+k).value]))}));bind('save-report',()=>post({op:'save'}));
}
function effective(id){const n=state.nodes.find(n=>n.id===id);return n.mode==='custom'?n.acl:effective(n.parent);}
function person(id){const p=state.people.find(p=>p.id===id);return p.name+(p.email?' · '+p.email:'');}
function sharing(){
 const n=state.nodes.find(n=>n.id===selectedNode),acl=shareDraft?shareDraft.acl:effective(selectedNode);
 let html=`<h1>Shared Access</h1><div class="filelayout"><aside class="card"><h2>Documents</h2>${state.nodes.map(x=>button('node-'+x.id,esc(x.title),`class="folder ${x.id===selectedNode?'active':''}"`)).join('')}</aside><section class="card"><h2>${esc(n.title)}</h2><p>${shareDraft?'Editing custom access — unsaved':n.mode==='inherit'?'Inherited from Atlas project':'Custom access'}</p>`;
 if(!shareDraft)html+=button('edit-access',n.mode==='inherit'?'Customize access':'Edit access');
 html+='<table><thead><tr><th>Person or group</th><th>Role</th><th></th></tr></thead><tbody>'+acl.map(x=>`<tr><td>${esc(person(x.principal))}</td><td>${shareDraft?`<select id="role-${x.principal}">${['Owner','Editor','Viewer'].map(v=>`<option ${v===x.role?'selected':''}>${v}</option>`).join('')}</select>`:x.role}</td><td>${shareDraft?button('remove-'+x.principal,'Remove'):''}</td></tr>`).join('')+'</tbody></table>';
 if(shareDraft)html+=`<h3>Add person</h3><label>Person<select id="add-person">${state.people.filter(p=>!acl.some(a=>a.principal===p.id)).map(p=>`<option value="${p.id}">${esc(person(p.id))}</option>`).join('')}</select></label>${select('add-role','Role',['Viewer','Editor','Owner'],'Viewer')}<div class="toolbar">${button('add-access','Add person')}${button('save-access','Save changes')}${button('cancel-access','Cancel')}</div>`;
 html+='</section></div>';$('app').insertAdjacentHTML('beforeend',html);
 for(const x of state.nodes)bind('node-'+x.id,()=>{selectedNode=x.id;shareDraft=null;notice='';render();});
 bind('edit-access',()=>{shareDraft={acl:structuredClone(effective(selectedNode))};render();});bind('cancel-access',()=>{shareDraft=null;render();});
 if(shareDraft){
  for(const x of shareDraft.acl){$('role-'+x.principal).onchange=()=>{x.role=$('role-'+x.principal).value;};bind('remove-'+x.principal,()=>{shareDraft.acl=shareDraft.acl.filter(a=>a.principal!==x.principal);render();});}
  bind('add-access',()=>{const principal=$('add-person').value;if(principal){shareDraft.acl.push({principal,role:$('add-role').value});render();}});
  bind('save-access',()=>{const a={op:'set_access',node:selectedNode,mode:'custom',acl:structuredClone(shareDraft.acl)};shareDraft=null;post(a);});
 }
}
fetch('/api/state').then(r=>r.json()).then(s=>{state=s;render();});
