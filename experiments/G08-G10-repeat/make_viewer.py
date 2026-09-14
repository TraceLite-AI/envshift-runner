"""Build an offline viewer of original screenshots and their following actions."""
import json
from publish_workflow import ROOT

rows=json.loads((ROOT/'AGENT_RESULTS.json').read_text())
records=[]
for r in rows:
    path=ROOT/r['evidence'];loop=json.loads((path/'agent/loop.json').read_text())
    records.append({'task':r['task'],'trial':r['trial'],'reward':r['reward'],'valid':r['valid'],
                    'evidence':r['evidence'],'archive':r['archive'],'history':loop['history'],
                    'meta':r['meta'],'environment':r['environment']})
payload=json.dumps(records,ensure_ascii=False).replace('<','\\u003c')
html='''<!doctype html>
<html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>G08 / G10 · GUI 复测证据</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#f4f6f8;color:#183248;font:15px system-ui,sans-serif}
header{padding:20px 28px;background:#183e58;color:white}h1{margin:0 0 8px;font-size:23px}p{line-height:1.6;margin:8px 0}
nav{display:flex;gap:12px;align-items:center;flex-wrap:wrap;padding:16px 28px;background:white;border-bottom:1px solid #ccd5db}
select,button{font:inherit;padding:7px 12px;border:1px solid #b7c5cd;border-radius:5px;background:white;color:#183248}
button{cursor:pointer}button:disabled{opacity:.4;cursor:default}input[type=range]{flex:1;min-width:140px;max-width:440px}
main{display:grid;grid-template-columns:minmax(0,1fr) 350px;gap:20px;padding:22px}figure{margin:0}img{width:100%;height:auto;display:block;border:1px solid #bdc9d1;background:#101010}
figcaption{padding:10px 0;color:#526675}aside{background:white;padding:18px;border:1px solid #dce2e7;border-radius:6px;overflow:auto}
h2{font-size:17px;margin:0 0 12px}h3{font-size:15px;margin-top:22px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:13px/1.6 ui-monospace,monospace;background:#f1f4f6;padding:12px;border-radius:4px}
a{color:#12608d}.failure{color:#ae3540;font-weight:700}.pass{color:#267344;font-weight:700}#notice{padding:0 28px;color:#536572}
@media(max-width:1000px){main{grid-template-columns:1fr}aside{max-height:none}}
</style>
<header><h1>G08 / G10 · GUI 复测证据</h1><div>Ubuntu · gemini-3.5-flash · gui_native_v2 · 每轮 60 步</div></header>
<nav><label>试验 <select id="trial"></select></label><button id="prev">上一张</button><input id="step" type="range" min="1" value="1" aria-label="截图步骤"><button id="next">下一张</button><span id="counter"></span><span id="verdict"></span></nav>
<p id="notice">截图未经改动。第 N 张是模型执行第 N 个动作前看到的屏幕；最后一张是最终动作后的屏幕。键盘左右箭头可切换。</p>
<main><figure><img id="screen" alt="原始 GUI 截图"><figcaption id="caption"></figcaption></figure><aside><h2 id="label"></h2><pre id="action"></pre><p id="execution"></p><h3>验收与业务写入</h3><pre id="audit"></pre><h3>原始证据</h3><p><a id="archive">下载完整压缩证据</a></p><p><a id="trace">动作 JSON</a> · <a id="meta">最终状态与判分</a></p><p><a href="REPORT.md">报告</a> · <a href="OBSERVATIONS.md">行为分析</a></p></aside></main>
<script id="data" type="application/json">__DATA__</script>
<script>
const records=JSON.parse(document.getElementById('data').textContent),$=id=>document.getElementById(id);
const picker=$('trial'), slider=$('step');
for(let i=0;i<records.length;i++){const r=records[i],o=document.createElement('option');o.value=i;o.textContent=r.task+' · 第 '+r.trial+' 次';picker.append(o)}
function render(){
 const r=records[Number(picker.value)];if(!r)return;
 slider.max=r.history.length+1;const n=Number(slider.value),final=n>r.history.length,h=final?null:r.history[n-1];
 $('screen').src=r.evidence+'/'+(final?'agent-final.png':'agent/step'+String(n).padStart(2,'0')+'.png');
 $('counter').textContent=n+' / '+(r.history.length+1);
 $('caption').textContent=final?'最终动作后的屏幕':'执行动作 '+n+' 前，模型实际收到的截图';
 $('label').textContent=final?'任务最终状态':'随后执行的动作 '+n;
 $('action').textContent=JSON.stringify(final?{reward:r.reward,steps:r.history.length,valid:r.valid}:h.action,null,2);
 $('execution').textContent=final?'以业务判据判定结果，不使用模型的自我评价。':h.result;
 $('audit').textContent=JSON.stringify({checks:r.meta.checks,audit:r.meta.audit},null,2);
 $('verdict').textContent=!r.valid?'无效运行':r.reward===1?'交付成功':'交付失败';$('verdict').className=r.reward===1?'pass':'failure';
 $('archive').href=r.archive;$('trace').href=r.evidence+'/agent/loop.json';$('meta').href=r.evidence+'/meta.json';
 $('prev').disabled=n===1;$('next').disabled=final;
}
picker.addEventListener('change',()=>{slider.value=1;render()});slider.addEventListener('input',render);
$('prev').onclick=()=>{slider.value=Math.max(1,Number(slider.value)-1);render()};
$('next').onclick=()=>{slider.value=Math.min(Number(slider.max),Number(slider.value)+1);render()};
document.addEventListener('keydown',e=>{if(e.target.matches('select,input'))return;if(e.key==='ArrowLeft')$('prev').click();if(e.key==='ArrowRight')$('next').click()});render();
</script></html>'''
(ROOT/'VIEWER.html').write_text(html.replace('__DATA__',payload))
print('VIEWER.html:',len(records),'trials')
