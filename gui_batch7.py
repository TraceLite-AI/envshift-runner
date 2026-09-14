"""Five benchmark-inspired GUI workflows; agent sees screenshots only; reference uses DOM-assisted focus."""
import argparse, copy, hashlib, http.server, json, os, pathlib, platform
import shutil, subprocess, sys, tempfile, threading, time, urllib.parse, urllib.request
from task_world import PROMPTS, TITLES, GUARD, fixture, apply, grade, expected_actions
import scroll_probe
from task_server import TaskSession
from reference_ui import steps as reference_steps

def main():
    for stream in (sys.stdout,sys.stderr):stream.reconfigure(encoding='utf-8',errors='replace')
    ap=argparse.ArgumentParser();ap.add_argument('--task',choices=list(PROMPTS),required=True);ap.add_argument('--arm',choices=['control','agent'],required=True);ap.add_argument('--model',default='gemini-3.5-flash');ap.add_argument('--steps',type=int,default=60);a=ap.parse_args()
    here=pathlib.Path(__file__).resolve().parent;out=here/'gui_batch7_out';out.mkdir(exist_ok=True)
    temp=pathlib.Path(tempfile.mkdtemp(prefix='envshift-gui-batch7-'));downloads=pathlib.Path.home()/'Downloads';downloads.mkdir(exist_ok=True)
    session=TaskSession(a.task,out/'artifacts');url=session.url
    def result():return session.result()
    if sys.platform=='darwin':chrome='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
    elif os.name=='nt':chrome=next(p for p in [r'C:\Program Files\Google\Chrome\Application\chrome.exe',r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'] if pathlib.Path(p).exists())
    else:chrome=shutil.which('google-chrome') or shutil.which('google-chrome-stable')
    cmd=[chrome,'--user-data-dir='+str(temp/'profile'),'--remote-debugging-port=0','--remote-allow-origins=*','--no-first-run','--no-default-browser-check','--disable-features=Translate','--lang=en-US','--window-position=0,0','--window-size=1200,850',url]
    if sys.platform.startswith('linux'):cmd+=['--no-sandbox','--disable-dev-shm-usage']
    chromeproc=subprocess.Popen(cmd,stdout=(out/'chrome.log').open('w'),stderr=subprocess.STDOUT)
    for _ in range(60):
        try:
            port=int((temp/'profile/DevToolsActivePort').read_text().splitlines()[0])
            with urllib.request.urlopen(f'http://127.0.0.1:{port}/json',timeout=3) as r:tabs=json.load(r)
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
    def wait_ready():
        for _ in range(100):
            if evaluate('document.documentElement && document.documentElement.dataset.ready === "true"'):return
            time.sleep(.1)
        raise RuntimeError('App did not finish initialization')
    cdp('Page.bringToFront');time.sleep(2)
    if sys.platform=='darwin':
        shot('startup-before-dismiss.png');pyautogui.click(453,321);time.sleep(.8);cdp('Page.bringToFront');pyautogui.click(900,650);time.sleep(.5)
    if os.name=='nt':
        # Protocol amendment: keep the browser client area inside the usable desktop.
        before=cdp('Browser.getWindowForTarget')
        pyautogui.hotkey('win','up');time.sleep(1.5)
        after=cdp('Browser.getWindowForTarget')
        (out/'window-fit.json').write_text(json.dumps({'before':before,'after':after,'screen_size':list(pyautogui.size()),'method':'physical Win+Up before trial'},indent=2),encoding='utf-8')
        shot('window-fit.png')
        if after.get('bounds',{}).get('windowState')!='maximized':raise RuntimeError('Windows browser did not maximize; not a valid trial')
    # Both arms start from a neutral task page after any OS startup focus clicks.
    cdp('Page.navigate',{'url':url});cdp('Page.bringToFront');time.sleep(1);wait_ready();shot('neutral-init.png')
    if a.arm=='control':scroll_probe.run(cdp,evaluate,shot,pyautogui,url,out)
    wait_ready();shot('initial.png');assert result()['reward']==0
    instruction=PROMPTS[a.task]+' '+GUARD
    (out/'fixture.json').write_text(json.dumps(fixture(a.task),indent=2),encoding='utf-8')
    (out/'instruction.txt').write_text(instruction,encoding='utf-8')
    (out/'environment.json').write_text(json.dumps({'platform':platform.platform(),'python':sys.version,'browser':cdp('Browser.getVersion'),'screen_size':list(pyautogui.size()),'task':a.task,'tool_version':'gui_native_v3_scroll','reference_assistance':'DOM focus, scrollIntoView and element geometry; physical keyboard/mouse activation only'},indent=2),encoding='utf-8')
    if a.arm=='control':
        results=[]
        for label in ['oracle','wrong-result']:
            session.reset()
            cdp('Page.navigate',{'url':url});cdp('Page.bringToFront');time.sleep(1)
            good=label=='oracle'
            wait_ready()
            for step in reference_steps(a.task,good):
                kind,name,*value=step
                if kind=='click':press(name)
                elif kind=='field':typefield(name,value[0])
                elif kind=='choose':choose(name,value[0])
                elif kind=='toggle':focus(name);pyautogui.press('space');time.sleep(.4)
                else:raise ValueError(kind)
            time.sleep(1);shot(label+'-final.png');r={'arm':label,**result()}
            shutil.copytree(out/'artifacts',out/(label+'-artifacts'),dirs_exist_ok=True)
            actual=copy.deepcopy(r['audit']);want=expected_actions(a.task,good)
            r['materialized']=actual==want
            results.append(r)
            (out/(label+'-result.json')).write_text(json.dumps(r,indent=2),encoding='utf-8')
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
        valid=rc==0 and bool(loop) and not loop.get('channel_fail') and not loop.get('blind_steps') and loop.get('tool_version')=='gui_native_v3_scroll'
        meta={'arm':'agent','task':a.task,'platform':platform.platform(),'model':a.model,'model_rc':rc,'timeout':timed_out,'steps':loop.get('steps'),'channel_fail':loop.get('channel_fail'),'blind_steps':loop.get('blind_steps'),'valid_model_run':valid,**result()}
        shot('agent-final.png');print('AGENT_RESULT',json.dumps(meta),flush=True)
    (out/'meta.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    key=os.environ.get('ENVSHIFT_API_KEY','')
    if key:
        for file in out.rglob('*'):
            if file.is_file() and file.suffix in ['.json','.txt','.log']:file.write_text(file.read_text(encoding='utf-8',errors='replace').replace(key,'[REDACTED]'),encoding='utf-8')
    session.close();chromeproc.terminate()
    if a.arm=='agent' and not meta['valid_model_run']:sys.exit(3)
if __name__=='__main__':main()
