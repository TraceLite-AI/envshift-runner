"""Headless UI smoke checks on synthetic local data; not scored model trials."""
import base64, copy, http.server, json, pathlib, subprocess, tempfile, threading, time, urllib.request
import websocket
from task_world import fixture,apply,grade,PROMPTS,TITLES,expected_actions
ROOT=pathlib.Path(__file__).resolve().parent
OUT=ROOT/'local_preview';OUT.mkdir(exist_ok=True)
task='G17';state=fixture(task)
class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def reply(self,data,ctype):
        self.send_response(200);self.send_header('Content-Type',ctype);self.end_headers();self.wfile.write(data)
    def do_GET(self):
        if self.path=='/api/state':return self.reply(json.dumps(state).encode(),'application/json')
        if self.path in ['/app.js','/app.css']:return self.reply((ROOT/self.path[1:]).read_bytes(),'text/javascript' if self.path.endswith('js') else 'text/css')
        self.reply(('<!doctype html><meta charset="utf-8"><link rel="stylesheet" href="/app.css"><header>'+TITLES[task]+'</header><nav id="nav"></nav><main><div id="app"></div></main><script>const TASK='+json.dumps(task)+'</script><script src="/app.js"></script>').encode(),'text/html')
    def do_POST(self):
        a=json.loads(self.rfile.read(int(self.headers['Content-Length'])));apply(task,state,a);self.reply(json.dumps(state).encode(),'application/json')
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start();url=f'http://127.0.0.1:{server.server_port}/'
profile=tempfile.mkdtemp(prefix='envshift-gui6-preview-')
chrome=subprocess.Popen(['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome','--headless=new','--user-data-dir='+profile,'--remote-debugging-port=0','--remote-allow-origins=*','--no-first-run','--no-default-browser-check','--window-size=1024,768',url],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
try:
    for _ in range(80):
        portfile=pathlib.Path(profile)/'DevToolsActivePort'
        if portfile.exists():break
        time.sleep(.1)
    port=int(portfile.read_text().splitlines()[0]);rid=0
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    tabs=json.load(opener.open(f'http://127.0.0.1:{port}/json'))
    ws=websocket.create_connection(next(t['webSocketDebuggerUrl'] for t in tabs if t.get('type')=='page'),timeout=10,http_no_proxy=['127.0.0.1','localhost'])
    def cdp(method,params=None):
        global rid
        rid+=1;ws.send(json.dumps({'id':rid,'method':method,'params':params or {}}))
        while True:
            r=json.loads(ws.recv())
            if r.get('id')==rid:
                if 'error' in r:raise RuntimeError(r['error'])
                return r.get('result',{})
    def ev(code):
        r=cdp('Runtime.evaluate',{'expression':code,'returnByValue':True,'awaitPromise':True})
        if 'exceptionDetails' in r:raise RuntimeError(r['exceptionDetails'])
        return r.get('result',{}).get('value')
    def click(id):ev('document.getElementById('+json.dumps(id)+').click()');time.sleep(.12)
    def field(id,value):ev('document.getElementById('+json.dumps(id)+').value='+json.dumps(str(value)))
    def shot(name):
        (OUT/(name+'.png')).write_bytes(base64.b64decode(cdp('Page.captureScreenshot',{'captureBeyondViewport':False})['data']))
    checks=[]
    for task in PROMPTS:
        state=fixture(task);cdp('Page.navigate',{'url':url})
        for _ in range(50):
            if ev('document.documentElement && document.documentElement.dataset.ready === "true" && typeof TASK !== "undefined" && TASK === '+json.dumps(task)):break
            time.sleep(.1)
        else:raise RuntimeError('App not ready')
        shot(task+'-initial')
        if task=='G17':
            for action in expected_actions(task):
                if action['op']=='cell':click('cell-'+action['address']);field('formula',action['value']);click('apply-cell')
                elif action['op']=='format':field('namebox',action['range']);click('go');field('format','Currency');click('apply-format')
                else:click('save-sheet')
        elif task=='G18':
            click('edit-AR-2026-09-23');field('event-date','2026-09-24');field('event-start','14:00');field('event-end','14:45');field('event-location','Room C');click('attendee-Noah');click('event-next');shot(task+'-scope');click('scope-this');click('confirm-event')
        elif task=='G19':
            for action in expected_actions(task):
                op=action['op']
                if op=='move':
                    click('slide-'+action['id']);current=next(i for i,x in enumerate(state['slides']) if x['id']==action['id']);click('move-up' if action['index']<current else 'move-down')
                elif op=='hidden':click('slide-appendix');click('hidden')
                elif op=='notes':click('slide-next');field('notes',action['value']);click('save-notes')
                else:click('save-deck')
        else:
            click('folder-Shared/Handoffs');click('new-folder');field('folder-name','Atlas Release');click('create-folder')
            for action in expected_actions(task)[1:]:
                source=next(x for x in state['files'] if x['id']==action['id']);click('folder-'+source['path']);click('preview-'+action['id']);click('copy-file');field('destination',action['destination']);field('copy-name',action['name']);click('confirm-copy')
            click('folder-Shared/Handoffs/Atlas Release')
        assert grade(task,state)['reward']==1,(task,grade(task,state));shot(task+'-final')
        checks.append({'task':task,'ui_smoke_passed':True,'method':'headless Chrome DOM-assisted UI, not native GUI or model test'})
    (OUT/'CHECKS.json').write_text(json.dumps(checks,indent=2))
    print(json.dumps(checks))
finally:server.shutdown();chrome.terminate()
