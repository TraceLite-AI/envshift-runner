"""Native no-model scroll probe, called before controls on each fresh runner."""
import json,os,time,platform

HTML='''<!doctype html><html><meta charset="utf-8"><title>Scroll unit probe</title><style>body{margin:0;background:repeating-linear-gradient(#dceaf1 0px,#dceaf1 99px,#22485d 100px,#fff 101px,#fff 199px,#22485d 200px);height:18000px;font:24px Arial}h1{margin:0;padding:18px}p{padding:16px}</style><h1>Native scroll unit probe</h1><p>Known 100 px horizontal bands. Synthetic diagnostic page.</p><script>window.events=[];window.addEventListener('wheel',e=>events.push({dy:e.deltaY,dx:e.deltaX,mode:e.deltaMode}),{passive:true});</script></html>'''

def run(cdp,evaluate,shot,pyautogui,url,out):
    cdp('Page.navigate',{'url':url+'probe'});cdp('Page.bringToFront');time.sleep(1)
    width,height=pyautogui.size();pyautogui.moveTo(width//2,min(height-150,450),duration=.2);pyautogui.click();time.sleep(.3)
    rows=[]
    for mode in ['legacy','v3']:
        for dy in [-3,-5]:
            evaluate('window.scrollTo(0,0);window.events=[];true');time.sleep(.4)
            arg=dy*(120 if mode=='v3' and os.name=='nt' else 1)
            pyautogui.scroll(arg);time.sleep(1)
            info=evaluate('({scrollY:window.scrollY,events:window.events,innerHeight:window.innerHeight})')
            rows.append({'mode':mode,'requested_dy':dy,'native_argument':arg,**info});shot('scroll-'+mode+'-'+str(abs(dy))+'.png')
    passed=all(r['scrollY']>=20 and r['events'] for r in rows if r['mode']=='v3')
    data={'platform':platform.platform(),'method':'native pyautogui; CDP only initializes/resets diagnostic page and observes actual wheel events/scrollY','passed':passed,'rows':rows,'scope':'input effect probe; no agent and no model-score causal comparison'}
    (out/'scroll-probe.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    print('SCROLL_PROBE',json.dumps(data),flush=True)
    if not passed:raise RuntimeError('SCROLL_PROBE_FAILED: v3 did not produce useful native scrolling')
    cdp('Page.navigate',{'url':url});cdp('Page.bringToFront');time.sleep(1)
