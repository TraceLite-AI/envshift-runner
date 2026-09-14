"""Synthetic reconciliation portal; the agent uses screenshots and native file selection."""
import argparse,hashlib,html,http.server,json,os,pathlib,platform,shutil,socketserver,subprocess,sys,tempfile,threading,time,urllib.request
from email.parser import BytesParser
from email.policy import default
for s in (sys.stdout,sys.stderr):s.reconfigure(encoding='utf-8',errors='replace')
p=argparse.ArgumentParser();p.add_argument('--arm',choices=['control','agent'],required=True);p.add_argument('--model',default='gemini-3.5-flash');p.add_argument('--steps',type=int,default=35)
a=p.parse_args();HERE=pathlib.Path(__file__).resolve().parent;OUT=HERE/'gui_submit_out';OUT.mkdir(exist_ok=True)
ROOT=pathlib.Path(tempfile.mkdtemp(prefix='envshift-gui-submit-'));INBOX=pathlib.Path.home()/'Documents'/'EnvShift Inbox';INBOX.mkdir(parents=True,exist_ok=True)
GOOD=b'account,month,approved_amount\nCedar,2026-08,1684.50\nMaple,2026-08,927.25\n'
BAD=b'account,month,approved_amount\nCedar,2026-08,1600.00\nMaple,2026-08,900.00\n'
TARGET=INBOX/'approved-2026-08.csv';TARGET.write_bytes(GOOD)
(INBOX/'approved-2026-07.csv').write_bytes(GOOD.replace(b'2026-08',b'2026-07'))
(INBOX/'approved-2026-08.csv.txt').write_bytes(BAD)
(INBOX/'draft-2026-08.csv').write_bytes(BAD)
STATE={'submissions':[]};LOCK=threading.Lock()
PAGE='''<!doctype html><html><head><meta charset="utf-8"><title>Cedar Finance - Monthly reconciliation</title><style>
body{font-family:Arial,sans-serif;background:#eef2f6;color:#162333;margin:0}main{margin:40px auto;padding:32px;background:white;max-width:800px;border-radius:12px}h1{font-size:27px}label{display:block;margin-top:22px;font-weight:bold}button,input{font:18px Arial;padding:12px;margin-top:10px}button{background:#174f87;color:white;border:0;border-radius:6px;cursor:pointer}input[type=text]{width:320px}code{display:block;overflow-wrap:anywhere;margin:14px 0;padding:12px;background:#edf2f8}#chosen{margin-left:14px}#status{margin-top:24px;font-size:20px;color:#174f87}.hint{color:#46566b;line-height:1.6}</style></head><body><main>
<h1>Monthly reconciliation submission</h1><p class="hint">August 2026 · Upload the approved CSV and enter the batch reference.</p>
<p class="hint">Finance working folder:</p><code>FOLDER_PATH</code>
<label>1. Reconciliation file</label><button id="choose" autofocus onclick="document.getElementById('file').click()">Choose file</button><span id="chosen">No file selected</span><input type="file" id="file" style="display:none" onchange="document.getElementById('chosen').textContent=this.files[0]?.name||'No file selected'">
<label for="reference">2. Batch reference</label><input id="reference" type="text" autocomplete="off" placeholder="e.g. AUG-2026"><br>
<button id="submit" onclick="submitFile()">Submit reconciliation</button><div id="status"></div>
<script>async function submitFile(){const f=document.getElementById('file').files[0];if(!f){document.getElementById('status').textContent='Please choose a file.';return;}const d=new FormData();d.append('document',f);d.append('reference',document.getElementById('reference').value);const res=await fetch('/submit',{method:'POST',body:d});if(res.ok){document.getElementById('status').textContent='Submission received.';}}</script></main></body></html>'''.replace('FOLDER_PATH',html.escape(str(INBOX)))
class Handler(http.server.BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_GET(self):
  if self.path not in ('/','/favicon.ico'):self.send_error(404);return
  body=PAGE.encode('utf-8') if self.path=='/' else b''
  self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
 def do_POST(self):
  if self.path!='/submit':self.send_error(404);return
  body=self.rfile.read(int(self.headers['Content-Length']))
  message=BytesParser(policy=default).parsebytes(('Content-Type: '+self.headers['Content-Type']+'\r\nMIME-Version: 1.0\r\n\r\n').encode()+body)
  rec={}
  for part in message.iter_parts():
   name=part.get_param('name',header='content-disposition');value=part.get_payload(decode=True)
   if name=='document':rec.update(filename=part.get_filename(),sha256=hashlib.sha256(value).hexdigest(),size=len(value))
   elif name=='reference':rec['reference']=value.decode('utf-8')
  with LOCK:STATE['submissions'].append(rec)
  self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(b'{"received":true}')
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start();URL=f'http://127.0.0.1:{server.server_port}/'

def chrome_bin():
 if sys.platform=='darwin':return '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
 if os.name=='nt':
  for path in (r'C:\Program Files\Google\Chrome\Application\chrome.exe',r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'):
   if pathlib.Path(path).exists():return path
 return shutil.which('google-chrome') or shutil.which('google-chrome-stable') or shutil.which('chromium')
chrome=chrome_bin();assert chrome and pathlib.Path(chrome).is_file(),'Chrome missing'
args=[chrome,'--user-data-dir='+str(ROOT/'profile'),'--remote-debugging-port=9222','--remote-allow-origins=*','--no-first-run','--no-default-browser-check','--disable-session-crashed-bubble','--disable-features=Translate','--lang=en-US','--window-position=0,0','--window-size=1200,850',URL]
if sys.platform.startswith('linux'):args+=['--no-sandbox','--disable-dev-shm-usage']
CHROME=subprocess.Popen(args,stdout=(OUT/'chrome.log').open('w'),stderr=subprocess.STDOUT)

def tabs():
 with urllib.request.urlopen('http://127.0.0.1:9222/json',timeout=3) as f:return json.load(f)
for _ in range(60):
 try:
  target=next(t for t in tabs() if t.get('url')==URL);break
 except Exception:time.sleep(1)
else:raise RuntimeError('Chrome page did not start')
import websocket
ws=websocket.create_connection(target['webSocketDebuggerUrl'],timeout=10);rid=0

def cdp(method,params=None):
 global rid
 rid+=1;ws.send(json.dumps(dict(id=rid,method=method,params=params or {})))
 while True:
  data=json.loads(ws.recv())
  if data.get('id')==rid:
   if 'error' in data:raise RuntimeError(data['error'])
   return data.get('result',{})
def evaluate(expression):return cdp('Runtime.evaluate',{'expression':expression,'returnByValue':True}).get('result',{}).get('value')
cdp('Page.bringToFront');time.sleep(2)
import mss,pyautogui
from PIL import Image
pyautogui.FAILSAFE=False

def screenshot(name):
 with mss.mss() as cap:
  raw=cap.grab(cap.monitors[1]);im=Image.frombytes('RGB',raw.size,raw.rgb);im.save(OUT/name)
 return im.size

def grade():
 with LOCK:records=list(STATE['submissions'])
 last=records[-1] if records else {}
 checks=dict(submitted=bool(records),correct_filename=last.get('filename')==TARGET.name,correct_bytes=last.get('sha256')==hashlib.sha256(GOOD).hexdigest(),correct_reference=last.get('reference')=='AUG-2026')
 return dict(reward=int(all(checks.values())),checks=checks,submissions=records)

screenshot('initial.png');assert grade()['reward']==0
model_meta=None
if a.arm=='control':
 results=[]
 for label,path in [('oracle',TARGET),('wrong-file',INBOX/'approved-2026-08.csv.txt')]:
  with LOCK:STATE['submissions'].clear()
  cdp('Page.navigate',{'url':URL});time.sleep(1)
  evaluate("document.getElementById('choose').focus()");pyautogui.press('enter');time.sleep(2);screenshot(label+'-dialog.png')
  if sys.platform=='darwin':
   pyautogui.hotkey('command','shift','g');time.sleep(.7);pyautogui.write(str(path),interval=.01);pyautogui.press('enter');time.sleep(1);pyautogui.press('enter')
  elif os.name=='nt':
   pyautogui.hotkey('alt','n');pyautogui.write(str(path),interval=.01);pyautogui.press('enter')
  else:
   pyautogui.click(87,84);time.sleep(.5);pyautogui.doubleClick(285,106,interval=.12);time.sleep(.6);screenshot(label+'-documents.png');pyautogui.doubleClick(285,106,interval=.12);time.sleep(.6);screenshot(label+'-inbox.png');pyautogui.click(350,130 if label=='oracle' else 155);time.sleep(.3);screenshot(label+'-row-selected.png');pyautogui.click(1110,820)
  time.sleep(2);screenshot(label+'-chosen.png')
  chosen=evaluate("document.getElementById('file').files[0]?.name||''")
  if chosen!=path.name:
   raise RuntimeError('NATIVE_CHOOSER_CONTROL_FAILED '+repr(chosen))
  evaluate("document.getElementById('reference').focus()");pyautogui.write('AUG-2026',interval=.05)
  evaluate("document.getElementById('submit').focus()");pyautogui.press('enter');time.sleep(1)
  result=grade();result['arm']=label;results.append(result);screenshot(label+'-submitted.png')
  print('CONTROL',platform.system(),label,json.dumps(result),flush=True)
  assert result['reward']==int(label=='oracle')
 meta=dict(arm=a.arm,platform=platform.platform(),results=results,control_passed=True)
else:
 # The agent process has screenshot/mouse/keyboard actions only; CDP stays in the controller.
 instruction=(f'Use the Chrome page already open to submit the approved August 2026 reconciliation. '
              f'The exact file is approved-2026-08.csv in {INBOX}. Do not use the .csv.txt copy, draft, or July file. '
              f'Enter batch reference AUG-2026 and submit. Use visible application UI only: do not open a terminal or DevTools, execute code, or browse other sites.')
 ws.close() # no controller interaction with the page during agent actions
 proc=subprocess.run([sys.executable,str(HERE/'gui_agent_loop.py'),'--task','G01-native-file-submit','--model',a.model,'--max-steps',str(a.steps),'--instruction',instruction,'--outdir',str(OUT/'agent')],capture_output=True,timeout=1500)
 (OUT/'agent.log').write_bytes(proc.stdout+proc.stderr)
 loop_path=OUT/'agent/loop.json';loop=json.loads(loop_path.read_text(encoding='utf-8')) if loop_path.exists() else {}
 result=grade();meta=dict(arm=a.arm,platform=platform.platform(),model=a.model,model_rc=proc.returncode,steps=loop.get('steps'),channel_fail=loop.get('channel_fail'),blind_steps=loop.get('blind_steps'),valid_model_run=proc.returncode==0 and bool(loop) and not loop.get('channel_fail') and not loop.get('blind_steps'),**result)
 screenshot('agent-final.png')
 print('AGENT_RESULT',json.dumps(meta),flush=True)
(OUT/'meta.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
# All documents and page state are synthetic. Redact the exact API credential before artifact upload.
key=os.environ.get('ENVSHIFT_API_KEY','')
if key:
 for file in OUT.rglob('*'):
  if file.is_file() and file.suffix in ('.json','.log','.txt'):
   text=file.read_text(encoding='utf-8',errors='replace');file.write_text(text.replace(key,'[REDACTED]'),encoding='utf-8')
server.shutdown();CHROME.terminate()
if a.arm=='agent' and not meta['valid_model_run']:sys.exit(3)
