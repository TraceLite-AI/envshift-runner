"""Three synthetic GUI tasks. No model-facing shell, DOM, or file APIs."""
import argparse, hashlib, html, http.server, json, os, pathlib, platform
import shutil, subprocess, sys, tempfile, threading, time, urllib.request
from email.parser import BytesParser
from email.policy import default

for stream in (sys.stdout, sys.stderr):
    stream.reconfigure(encoding='utf-8', errors='replace')
ap = argparse.ArgumentParser()
ap.add_argument('--task', choices=['G02', 'G03', 'G04'], required=True)
ap.add_argument('--arm', choices=['control', 'agent'], required=True)
ap.add_argument('--model', default='gemini-3.5-flash')
ap.add_argument('--steps', type=int, default=45)
a = ap.parse_args()
HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / 'gui_batch2_out'; OUT.mkdir(exist_ok=True)
TEMP = pathlib.Path(tempfile.mkdtemp(prefix='envshift-gui-batch2-'))
WORK = pathlib.Path.home() / 'Documents' / ('EnvShift ' + a.task)
WORK.mkdir(parents=True, exist_ok=True)
FILES = {name: ('document,approved_amount\n' + name + ',125.50\n').encode()
         for name in ['01-invoice.csv','02-draft.csv','03-receipt.csv','04-old.csv','05-approval.csv']}
WANTED = ['01-invoice.csv','03-receipt.csv','05-approval.csv']
SNAPSHOT = WORK / 'approved-snapshot.html'
STALE = b'<!doctype html><title>Old snapshot</title><h1>JULY-OLD-REVISION</h1>'
if a.task == 'G02':
    for name, data in FILES.items(): (WORK / name).write_bytes(data)
if a.task == 'G04': SNAPSHOT.write_bytes(STALE)
STATE = []; LOCK = threading.Lock()
STYLE = '''body{font-family:Arial,sans-serif;background:#eef2f6;color:#14293f;margin:0}main{max-width:800px;margin:32px auto;background:white;padding:28px;border-radius:12px}h1{font-size:27px}button,input,select{font:18px Arial;padding:10px;margin:8px 0}button{background:#174f87;color:white;border:0;border-radius:6px}label{display:block;margin-top:12px}code{display:block;background:#edf2f8;padding:10px;overflow-wrap:anywhere}li{line-height:1.8}table{border-collapse:collapse;width:100%}td,th{border:1px solid #bbc9d5;padding:12px;text-align:left}#status{font-size:20px;color:#174f87;margin-top:18px}'''
GUARD = 'Use visible application UI only. Do not open a terminal or DevTools, execute code, or browse other websites.'
if a.task == 'G02':
    title = 'Invoice batch attachments'
    content = '''<h1>Invoice batch attachments</h1><p>Prepare the approved billing packet. Select all three required CSV attachments, then submit the batch.</p><p>Working folder:</p><code>FOLDER</code><p>Required files: <b>01-invoice.csv, 03-receipt.csv, 05-approval.csv</b>. Exclude the draft and old copy.</p><button id="choose" onclick="document.getElementById('files').click()">Choose attachments</button><input id="files" type="file" multiple style="display:none" onchange="showFiles()"><ul id="chosen"><li>No attachments</li></ul><button id="submit" onclick="sendBatch()">Submit batch</button><div id="status"></div><script>function showFiles(){document.getElementById('chosen').replaceChildren(...Array.from(document.getElementById('files').files,f=>{const n=document.createElement('li');n.textContent=f.name;return n;}));}async function sendBatch(){const fs=document.getElementById('files').files;if(!fs.length){document.getElementById('status').textContent='Choose attachments first.';return;}const d=new FormData();for(const f of fs)d.append('document',f);await fetch('/submit',{method:'POST',body:d});document.getElementById('status').textContent='Batch received.';}</script>'''.replace('FOLDER',html.escape(str(WORK)))
    instruction = f'Submit the billing packet on the open Chrome page. Attach exactly these three files from {WORK}: {", ".join(WANTED)}. Exclude 02-draft.csv and 04-old.csv. Submit the batch. ' + GUARD
elif a.task == 'G03':
    title = 'Pickup scheduling'
    content = '''<h1>Change the pickup appointment</h1><p>Requested pickup: <b>September 2, 2026</b>. Service: <b>Express</b>. Reference: <b>PICKUP-209</b>.</p><p>The draft below still has the previous appointment. Update it and save.</p><label for="date">Pickup date</label><input type="date" id="date" value="2026-08-31"><label for="service">Service</label><select id="service"><option>Standard</option><option>Express</option></select><label for="reference">Reference</label><input id="reference" value="DRAFT-208"><br><button id="submit" onclick="save()">Save appointment</button><div id="status"></div><script>async function save(){const d={date:document.getElementById('date').value,service:document.getElementById('service').value,reference:document.getElementById('reference').value};await fetch('/submit',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)});document.getElementById('status').textContent='Appointment saved.';}</script>'''
    instruction = 'Update the pickup appointment on the open Chrome page to September 2, 2026, choose Express service, replace the reference with PICKUP-209, and save the appointment. ' + GUARD
else:
    title = 'approved-snapshot'
    content = '''<h1>Approved reconciliation snapshot</h1><p>Revision: <b>AUG26-APPROVED-R4</b></p><table><tr><th>Account</th><th>Approved amount</th></tr><tr><td>Cedar</td><td>1684.50</td></tr><tr><td>Maple</td><td>927.25</td></tr></table><p>Archive this page as <b>approved-snapshot.html</b> in the folder below, replacing the old July snapshot. Preserve the content of this page.</p><code>FOLDER</code><p>Use Chrome's Save page / Save as function. An HTML page, with or without its supporting folder, is accepted.</p>'''.replace('FOLDER',html.escape(str(WORK)))
    instruction = f'Save the currently open approved reconciliation snapshot webpage as approved-snapshot.html in {WORK}, replacing the existing old July snapshot. Keep the page content intact. Use Chrome Save page / Save as; either HTML only or a complete webpage is accepted. ' + GUARD
PAGE = f'<!doctype html><html><head><meta charset="utf-8"><title>{title}</title><style>{STYLE}</style></head><body><main>{content}</main></body></html>'

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def do_GET(self):
        body = PAGE.encode() if self.path == '/' else b''
        self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_POST(self):
        if self.path != '/submit': self.send_error(404); return
        data = self.rfile.read(int(self.headers['Content-Length']))
        if self.headers['Content-Type'].startswith('application/json'):
            record = json.loads(data)
        else:
            message = BytesParser(policy=default).parsebytes(('Content-Type: '+self.headers['Content-Type']+'\r\nMIME-Version: 1.0\r\n\r\n').encode()+data)
            record = {'files': []}
            for part in message.iter_parts():
                if part.get_param('name',header='content-disposition') == 'document':
                    payload = part.get_payload(decode=True)
                    record['files'].append({'name':part.get_filename(),'sha256':hashlib.sha256(payload).hexdigest(),'size':len(payload)})
        with LOCK: STATE.append(record)
        self.send_response(200); self.end_headers(); self.wfile.write(b'{"received":true}')
server = http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
URL = f'http://127.0.0.1:{server.server_port}/'

def grade():
    with LOCK: records = list(STATE)
    last = records[-1] if records else {}
    if a.task == 'G02':
        files = last.get('files',[])
        expected = {n:hashlib.sha256(FILES[n]).hexdigest() for n in WANTED}
        checks = {'submitted':bool(records),'exact_file_set':len(files)==3 and {f['name'] for f in files}==set(WANTED),'correct_bytes':len(files)==3 and all(expected.get(f['name'])==f['sha256'] for f in files)}
    elif a.task == 'G03':
        checks = {'submitted':bool(records),'correct_date':last.get('date')=='2026-09-02','correct_service':last.get('service')=='Express','correct_reference':last.get('reference')=='PICKUP-209'}
    else:
        data = SNAPSHOT.read_bytes() if SNAPSHOT.exists() else b''
        checks = {'target_exists':SNAPSHOT.is_file(),'approved_revision':b'AUG26-APPROVED-R4' in data,'old_revision_removed':b'JULY-OLD-REVISION' not in data,'accounts_preserved':all(v in data for v in [b'Cedar',b'1684.50',b'Maple',b'927.25'])}
        records = [{'target':str(SNAPSHOT),'size':len(data),'sha256':hashlib.sha256(data).hexdigest(),'files_in_output':sorted(p.name for p in WORK.iterdir())}]
    return {'reward':int(all(checks.values())),'checks':checks,'submissions':records}

def chrome_path():
    if sys.platform=='darwin': return '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
    if os.name=='nt':
        for p in [r'C:\Program Files\Google\Chrome\Application\chrome.exe',r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe']:
            if pathlib.Path(p).is_file():return p
    return shutil.which('google-chrome') or shutil.which('google-chrome-stable')
chrome = chrome_path(); assert chrome
cmd = [chrome,'--user-data-dir='+str(TEMP/'profile'),'--remote-debugging-port=9222','--remote-allow-origins=*','--no-first-run','--no-default-browser-check','--disable-features=Translate','--lang=en-US','--window-position=0,0','--window-size=1200,850',URL]
if sys.platform.startswith('linux'):cmd += ['--no-sandbox','--disable-dev-shm-usage']
CHROME = subprocess.Popen(cmd,stdout=(OUT/'chrome.log').open('w'),stderr=subprocess.STDOUT)
for _ in range(60):
    try:
        with urllib.request.urlopen('http://127.0.0.1:9222/json',timeout=3) as response: tabs=json.load(response)
        target = next(t for t in tabs if t.get('url')==URL);break
    except Exception:time.sleep(1)
else:raise RuntimeError('Chrome did not start')
import websocket, mss, pyautogui
from PIL import Image
pyautogui.FAILSAFE=False
def click(x,y):
    pyautogui.moveTo(x,y,duration=.2);time.sleep(.15);pyautogui.click();time.sleep(.2)
ws = websocket.create_connection(target['webSocketDebuggerUrl'],timeout=10); rid=0

def cdp(method,params=None):
    global rid
    rid+=1;ws.send(json.dumps({'id':rid,'method':method,'params':params or {}}))
    while True:
        result=json.loads(ws.recv())
        if result.get('id')==rid:
            if 'error' in result:raise RuntimeError(result['error'])
            return result.get('result',{})
def evaluate(code):return cdp('Runtime.evaluate',{'expression':code,'returnByValue':True}).get('result',{}).get('value')
def focus(name):
    evaluate(f'document.getElementById({json.dumps(name)}).focus()');time.sleep(.3)
def screenshot(name):
    with mss.mss() as cap:
        raw=cap.grab(cap.monitors[1]);Image.frombytes('RGB',raw.size,raw.rgb).save(OUT/name)
def select_all():pyautogui.hotkey('command' if sys.platform=='darwin' else 'ctrl','a')
cdp('Page.bringToFront');time.sleep(2)
if sys.platform=='darwin':
    # The Python controller can cause a local-network startup prompt. Clear it
    # through visible UI before either control or agent work starts.
    screenshot('startup-before-dismiss.png');click(453,321);time.sleep(.8)
    cdp('Page.bringToFront');click(900,650);time.sleep(.5)
screenshot('initial.png')
assert grade()['reward']==0
(OUT/'instruction.txt').write_text(instruction,encoding='utf-8')
(OUT/'environment.json').write_text(json.dumps({'platform':platform.platform(),'python':sys.version,'browser':cdp('Browser.getVersion'),'screen_size':list(pyautogui.size()),'task':a.task},indent=2),encoding='utf-8')

if a.arm=='control':
    results=[]
    for label in ['oracle','wrong-result']:
        with LOCK:STATE.clear()
        if a.task=='G04': SNAPSHOT.write_bytes(STALE)
        cdp('Page.navigate',{'url':URL});time.sleep(1)
        if a.task=='G02':
            focus('choose');pyautogui.press('enter');time.sleep(2);screenshot(label+'-chooser.png')
            names=WANTED if label=='oracle' else list(FILES)
            if os.name=='nt':
                pyautogui.hotkey('alt','n');time.sleep(.3);pyautogui.write(' '.join('"'+str(WORK/n)+'"' for n in names),interval=.025);pyautogui.press('enter')
            elif sys.platform=='darwin':
                pyautogui.hotkey('command','shift','g');time.sleep(.6);pyautogui.write(str(WORK),interval=.01);pyautogui.press('enter');time.sleep(1);screenshot(label+'-folder.png')
                click(560,220)
                if label=='oracle':
                    pyautogui.keyDown('command');click(560,264);click(560,308);pyautogui.keyUp('command')
                else:select_all()
                screenshot(label+'-selected.png');click(855,558)
            else:
                click(87,84);time.sleep(.4);pyautogui.doubleClick(285,104,interval=.12);time.sleep(.5);pyautogui.doubleClick(285,104,interval=.12);time.sleep(.6);screenshot(label+'-folder.png');click(350,104)
                if label=='oracle':
                    pyautogui.keyDown('ctrl');click(350,150);click(350,196);pyautogui.keyUp('ctrl')
                else:select_all()
                screenshot(label+'-selected.png');click(1110,820)
            time.sleep(2);screenshot(label+'-chosen.png');focus('submit');pyautogui.press('enter')
        elif a.task=='G03':
            focus('date');pyautogui.write('09022026' if label=='oracle' else '09032026',interval=.08);pyautogui.press('tab')
            focus('service');pyautogui.press('e');pyautogui.press('tab')
            focus('reference');
            if os.name=='nt':click(250,513)
            select_all();pyautogui.write('PICKUP-209',interval=.08)
            focus('submit');pyautogui.press('enter')
        else:
            name='approved-snapshot.html' if label=='oracle' else 'approved-snapshot-copy.html'
            pyautogui.hotkey('command' if sys.platform=='darwin' else 'ctrl','s');time.sleep(2);screenshot(label+'-save-dialog.png')
            if sys.platform=='darwin':
                pyautogui.hotkey('command','shift','g');time.sleep(.6);pyautogui.write(str(WORK),interval=.01);pyautogui.press('enter');time.sleep(1);screenshot(label+'-save-folder.png');select_all();pyautogui.write(name,interval=.02)
            elif os.name=='nt':
                pyautogui.hotkey('alt','n');select_all();pyautogui.write(str(WORK/name),interval=.01)
            else:
                click(87,98);time.sleep(.4);pyautogui.doubleClick(285,158,interval=.12);time.sleep(.5);pyautogui.doubleClick(285,158,interval=.12);time.sleep(.6)
                screenshot(label+'-save-folder.png');click(420,47);select_all();pyautogui.write(name,interval=.02)
            if sys.platform.startswith('linux'):
                pyautogui.press('tab');click(1050,774);pyautogui.press('home');pyautogui.press('enter');time.sleep(.5)
                screenshot(label+'-save-format.png');click(1110,820)
            else:pyautogui.press('enter')
            time.sleep(1.5);screenshot(label+'-overwrite.png')
            if sys.platform=='darwin' and label=='oracle':click(570,474)
            else:
                if os.name=='nt':pyautogui.press('left')
                pyautogui.press('enter')
        time.sleep(2);screenshot(label+'-final.png')
        result={'arm':label,**grade()};results.append(result);print('CONTROL_RESULT',a.task,platform.system(),json.dumps(result),flush=True)
        if result['reward']!=int(label=='oracle'):
            if sys.platform.startswith('linux'):
                with (OUT/'window-tree.txt').open('w') as dump:
                    subprocess.run(['xwininfo','-root','-tree'],stdout=dump,stderr=subprocess.STDOUT)
            (OUT/'control-failure.json').write_text(json.dumps(result,indent=2));raise RuntimeError('GUI_CONTROL_FAILED '+a.task+' '+label)
    meta={'arm':'control','task':a.task,'platform':platform.platform(),'control_passed':True,'results':results}
else:
    ws.close()
    with (OUT/'agent.log').open('wb') as log:
        proc=subprocess.run([sys.executable,str(HERE/'gui_agent_loop.py'),'--task',a.task,'--model',a.model,'--max-steps',str(a.steps),'--instruction',instruction,'--outdir',str(OUT/'agent')],stdout=log,stderr=subprocess.STDOUT,timeout=1800)
    try:loop=json.loads((OUT/'agent/loop.json').read_text(encoding='utf-8'))
    except (OSError,ValueError):loop={}
    valid=proc.returncode==0 and bool(loop) and not loop.get('channel_fail') and not loop.get('blind_steps') and loop.get('coordinate_mode')=='normalized_0_1000'
    meta={'arm':'agent','task':a.task,'platform':platform.platform(),'model':a.model,'model_rc':proc.returncode,'steps':loop.get('steps'),'channel_fail':loop.get('channel_fail'),'blind_steps':loop.get('blind_steps'),'valid_model_run':valid,**grade()}
    screenshot('agent-final.png');print('AGENT_RESULT',json.dumps(meta),flush=True)
    if a.task=='G04':shutil.copytree(WORK,OUT/'delivered',dirs_exist_ok=True)
(OUT/'meta.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
key=os.environ.get('ENVSHIFT_API_KEY','')
if key:
    for file in OUT.rglob('*'):
        if file.is_file() and file.suffix in ['.json','.txt','.log']:
            file.write_text(file.read_text(encoding='utf-8',errors='replace').replace(key,'[REDACTED]'),encoding='utf-8')
server.shutdown();CHROME.terminate()
if a.arm=='agent' and not meta['valid_model_run']:sys.exit(3)
