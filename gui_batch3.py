"""Six GUI business tasks; agent sees screenshots only; reference uses DOM-assisted focus."""
import argparse, copy, hashlib, http.server, json, os, pathlib, platform
import shutil, subprocess, sys, tempfile, threading, time, urllib.parse, urllib.request
from task_world import PROMPTS, TITLES, GUARD, fixture, apply, grade, csv_bytes

def main():
    for stream in (sys.stdout,sys.stderr):stream.reconfigure(encoding='utf-8',errors='replace')
    ap=argparse.ArgumentParser();ap.add_argument('--task',choices=list(PROMPTS),required=True);ap.add_argument('--arm',choices=['control','agent'],required=True);ap.add_argument('--model',default='gemini-3.5-flash');ap.add_argument('--steps',type=int,default=60);a=ap.parse_args()
    here=pathlib.Path(__file__).resolve().parent;out=here/'gui_batch3_out';out.mkdir(exist_ok=True)
    temp=pathlib.Path(tempfile.mkdtemp(prefix='envshift-gui-batch3-'));downloads=pathlib.Path.home()/'Downloads';downloads.mkdir(exist_ok=True)
    targetfile=downloads/'approved-expenses.csv'
    if a.task=='G07' and targetfile.exists():raise RuntimeError('Synthetic export target already exists; refusing to overwrite during setup')
    state=fixture(a.task);audit=[];lock=threading.Lock()
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def respond(self,data,ctype='application/json',status=200,headers=None):
            self.send_response(status);self.send_header('Content-Type',ctype);self.send_header('Cache-Control','no-store')
            for k,v in (headers or {}).items():self.send_header(k,v)
            self.end_headers();self.wfile.write(data)
        def do_GET(self):
            parsed=urllib.parse.urlparse(self.path)
            if parsed.path=='/api/state':
                with lock:data=json.dumps(state).encode()
                return self.respond(data)
            if parsed.path=='/download.csv' and a.task=='G07':
                ids=urllib.parse.parse_qs(parsed.query).get('ids',[''])[0].split(',')
                with lock:
                    rows=[r for r in state['expenses'] if r['id'] in ids];data=csv_bytes(rows);state['exports'].append(ids);audit.append({'op':'export','ids':ids})
                return self.respond(data,'text/csv',headers={'Content-Disposition':'attachment; filename="approved-expenses.csv"'})
            if parsed.path in ['/app.js','/app.css']:
                return self.respond((here/parsed.path[1:]).read_bytes(),'text/javascript' if parsed.path.endswith('.js') else 'text/css')
            if parsed.path not in ['/','/orders']:return self.respond(b'Not found','text/plain',404)
            content='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+TITLES[a.task]+'</title><link rel="stylesheet" href="/app.css"><header>Cedar Workspace</header><main><div id="app"></div><div class="notice" id="message"></div></main><dialog id="dialog"><div id="dialog-body"></div></dialog><script>const TASK='+json.dumps(a.task)+';</script><script src="/app.js"></script></html>'
            self.respond(content.encode(),'text/html; charset=utf-8')
        def do_POST(self):
            try:
                action=json.loads(self.rfile.read(int(self.headers.get('Content-Length',0))))
                with lock:apply(a.task,state,action);audit.append(copy.deepcopy(action));data=json.dumps(state).encode()
                self.respond(data)
            except Exception as e:self.respond(json.dumps({'error':str(e)}).encode(),status=400)
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start();url=f'http://127.0.0.1:{server.server_port}/'
    def result():
        with lock:s=copy.deepcopy(state);events=copy.deepcopy(audit)
        data=targetfile.read_bytes() if a.task=='G07' and targetfile.exists() else None
        return {**grade(a.task,s,data),'state':s,'audit':events,'download_sha256':hashlib.sha256(data).hexdigest() if data else None}
    if sys.platform=='darwin':chrome='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
    elif os.name=='nt':chrome=next(p for p in [r'C:\Program Files\Google\Chrome\Application\chrome.exe',r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'] if pathlib.Path(p).exists())
    else:chrome=shutil.which('google-chrome') or shutil.which('google-chrome-stable')
    cmd=[chrome,'--user-data-dir='+str(temp/'profile'),'--remote-debugging-port=9222','--remote-allow-origins=*','--no-first-run','--no-default-browser-check','--disable-features=Translate','--lang=en-US','--window-position=0,0','--window-size=1200,850',url]
    if sys.platform.startswith('linux'):cmd+=['--no-sandbox','--disable-dev-shm-usage']
    chromeproc=subprocess.Popen(cmd,stdout=(out/'chrome.log').open('w'),stderr=subprocess.STDOUT)
    for _ in range(60):
        try:
            with urllib.request.urlopen('http://127.0.0.1:9222/json',timeout=3) as r:tabs=json.load(r)
            target=next(t for t in tabs if t.get('url')==url);break
        except Exception:time.sleep(1)
    else:raise RuntimeError('Chrome did not start')
    import websocket,mss,pyautogui
    from PIL import Image
    pyautogui.FAILSAFE=False
    ws=websocket.create_connection(target['webSocketDebuggerUrl'],timeout=10);rid=0
    def cdp(method,params=None):
        nonlocal rid
        rid+=1;ws.send(json.dumps({'id':rid,'method':method,'params':params or {}}))
        while True:
            r=json.loads(ws.recv())
            if r.get('id')==rid:
                if 'error' in r:raise RuntimeError(r['error'])
                return r.get('result',{})
    def evaluate(code):return cdp('Runtime.evaluate',{'expression':code,'returnByValue':True}).get('result',{}).get('value')
    def shot(name):
        with mss.mss() as cap:
            raw=cap.grab(cap.monitors[1]);Image.frombytes('RGB',raw.size,raw.rgb).save(out/name)
    def focus(name):
        code=f'(()=>{{const e=document.getElementById({json.dumps(name)});if(!e)throw Error("Missing element");e.scrollIntoView({{block:"center"}});e.focus();return document.activeElement===e}})()'
        if not evaluate(code):raise RuntimeError('Could not focus '+name)
        time.sleep(.35)
    def press(name):focus(name);pyautogui.press('enter');time.sleep(.65)
    def typefield(name,text):
        focus(name);pyautogui.hotkey('command' if sys.platform=='darwin' else 'ctrl','a');pyautogui.write(text,interval=.035);pyautogui.press('tab');time.sleep(.3)
    def choose(name,prefix):focus(name);pyautogui.write(prefix,interval=.15);pyautogui.press('tab');time.sleep(.6)
    def point(name):
        return evaluate(f'(()=>{{const r=document.getElementById({json.dumps(name)}).getBoundingClientRect();return [window.screenX+(window.outerWidth-window.innerWidth)/2+r.x+r.width/2,window.screenY+window.outerHeight-window.innerHeight+r.y+r.height/2]}})()')
    cdp('Page.bringToFront');time.sleep(2)
    if sys.platform=='darwin':
        shot('startup-before-dismiss.png');pyautogui.click(453,321);time.sleep(.8);cdp('Page.bringToFront');pyautogui.click(900,650);time.sleep(.5)
    shot('initial.png');assert result()['reward']==0
    instruction=PROMPTS[a.task]+' '+GUARD
    (out/'instruction.txt').write_text(instruction,encoding='utf-8')
    (out/'environment.json').write_text(json.dumps({'platform':platform.platform(),'python':sys.version,'browser':cdp('Browser.getVersion'),'screen_size':list(pyautogui.size()),'task':a.task,'tool_version':'gui_native_v2','reference_assistance':'DOM focus, scrollIntoView and element geometry; physical keyboard/mouse activation only'},indent=2),encoding='utf-8')
    if a.arm=='control':
        results=[]
        for label in ['oracle','wrong-result']:
            with lock:state=fixture(a.task);audit.clear()
            if a.task=='G07' and targetfile.exists():targetfile.unlink()
            cdp('Page.navigate',{'url':url});cdp('Page.bringToFront');time.sleep(1)
            good=label=='oracle'
            if a.task=='G05':
                press('edit-INV-044');press('orders');time.sleep(.8);shot(label+'-orders.png');pyautogui.hotkey('command' if sys.platform=='darwin' else 'ctrl','w');time.sleep(.6)
                typefield('total','611.00' if good else '604.70');typefield('reference','PO-6041');press('reconcile')
            elif a.task in ['G06','G07']:
                if a.task=='G06':
                    if good:press('clear')
                    choose('filter-customer','Cedar');choose('filter-status','Open');choose('filter-priority','High');press('all-matching');press('bulk');choose('owner','Mina');choose('new-status','Queued');typefield('tag','Reviewed');press('apply')
                else:
                    choose('filter-month','2026-09');choose('filter-status','Approved');choose('filter-department','Ops')
                    if good:press('all-matching')
                    else:focus('select-page');pyautogui.press('space');time.sleep(.5)
                    press('export');time.sleep(3)
            elif a.task=='G08':
                press('open-C-71');shot(label+'-notes.png');press('edit');typefield('street','27 Maasstraat');typefield('city','Rotterdam');typefield('postal','3011 AA');choose('contact','Email');press('save-draft')
                if good:press('publish')
            elif a.task=='G09':
                start=point('card-PROJ-218' if good else 'card-PROJ-281');end=point('drop-Review')
                pyautogui.moveTo(*start,duration=.3);pyautogui.mouseDown();time.sleep(.2);pyautogui.moveTo(start[0]+10,start[1]+5,duration=.2);pyautogui.moveTo(*end,duration=1);time.sleep(.3);pyautogui.mouseUp();time.sleep(1)
            elif a.task=='G10':
                press('policy');focus('policy-scroll');pyautogui.press('pagedown',presses=6,interval=.15);time.sleep(.6);shot(label+'-policy.png');press('ack');choose('route','Manager' if good else 'Standard');typefield('reason','EXP-7' if good else 'STD-1');press('submit-approval')
            time.sleep(1);shot(label+'-final.png');r={'arm':label,**result()};r['materialized']=bool(r['audit']);results.append(r)
            (out/(label+'-result.json')).write_text(json.dumps(r,indent=2),encoding='utf-8')
            if a.task=='G07' and targetfile.exists():shutil.copyfile(targetfile,out/(label+'-approved-expenses.csv'))
            print('CONTROL_RESULT',a.task,platform.system(),json.dumps(r),flush=True)
            if r['reward']!=int(good) or not r['materialized']:raise RuntimeError('GUI_CONTROL_FAILED '+a.task+' '+label)
        meta={'arm':'control','task':a.task,'platform':platform.platform(),'control_passed':True,'results':results}
    else:
        ws.close()
        timed_out=False
        with (out/'agent.log').open('wb') as log:
            try:proc=subprocess.run([sys.executable,str(here/'gui_agent_loop.py'),'--task',a.task,'--model',a.model,'--max-steps',str(a.steps),'--instruction',instruction,'--outdir',str(out/'agent')],stdout=log,stderr=subprocess.STDOUT,timeout=2100);rc=proc.returncode
            except subprocess.TimeoutExpired:rc=-1;timed_out=True
        try:loop=json.loads((out/'agent/loop.json').read_text(encoding='utf-8'))
        except (OSError,ValueError):loop={}
        valid=rc==0 and bool(loop) and not loop.get('channel_fail') and not loop.get('blind_steps') and loop.get('tool_version')=='gui_native_v2'
        meta={'arm':'agent','task':a.task,'platform':platform.platform(),'model':a.model,'model_rc':rc,'timeout':timed_out,'steps':loop.get('steps'),'channel_fail':loop.get('channel_fail'),'blind_steps':loop.get('blind_steps'),'valid_model_run':valid,**result()}
        shot('agent-final.png');print('AGENT_RESULT',json.dumps(meta),flush=True)
        if a.task=='G07' and targetfile.exists():shutil.copyfile(targetfile,out/'approved-expenses.csv')
    (out/'meta.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    key=os.environ.get('ENVSHIFT_API_KEY','')
    if key:
        for file in out.rglob('*'):
            if file.is_file() and file.suffix in ['.json','.txt','.log']:file.write_text(file.read_text(encoding='utf-8',errors='replace').replace(key,'[REDACTED]'),encoding='utf-8')
    server.shutdown();chromeproc.terminate()
    if a.arm=='agent' and not meta['valid_model_run']:sys.exit(3)
if __name__=='__main__':main()
