"""Open a task for manual review; Ctrl+C records the final state and grade locally."""
import argparse,copy,http.server,json,pathlib,threading,urllib.parse
from task_world import PROMPTS,TITLES,GUARD,fixture,apply,grade
p=argparse.ArgumentParser();p.add_argument('--task',choices=list(PROMPTS),required=True);p.add_argument('--out',default='manual-result.json');a=p.parse_args()
root=pathlib.Path(__file__).resolve().parent;state=fixture(a.task);audit=[];lock=threading.Lock()
class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def respond(self,data,ctype='application/json',status=200):
        self.send_response(status);self.send_header('Content-Type',ctype);self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(data)
    def do_GET(self):
        path=urllib.parse.urlparse(self.path).path
        if path=='/api/state':
            with lock:data=json.dumps(state).encode()
            return self.respond(data)
        if path in ['/app.js','/app.css']:return self.respond((root/path[1:]).read_bytes(),'text/javascript' if path.endswith('js') else 'text/css')
        if path!='/':return self.respond(b'Not found','text/plain',404)
        self.respond(('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+TITLES[a.task]+'</title><link rel="stylesheet" href="/app.css"><header>'+TITLES[a.task]+'</header><nav id="nav"></nav><main><div id="app"></div></main><script>const TASK='+json.dumps(a.task)+';</script><script src="/app.js"></script></html>').encode(),'text/html; charset=utf-8')
    def do_POST(self):
        try:
            action=json.loads(self.rfile.read(int(self.headers.get('Content-Length',0))))
            with lock:apply(a.task,state,action);audit.append(copy.deepcopy(action));data=json.dumps(state).encode()
            self.respond(data)
        except Exception as e:self.respond(json.dumps({'error':str(e)}).encode(),status=400)
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
print(PROMPTS[a.task]+' '+GUARD,flush=True)
print(f'Open http://127.0.0.1:{server.server_port}/ in a browser. Press Ctrl+C here when finished.',flush=True)
try:server.serve_forever()
except KeyboardInterrupt:pass
finally:
    server.server_close()
    with lock:result={'task':a.task,'kind':'manual_review_not_model_trial',**grade(a.task,state),'state':state,'audit':audit}
    pathlib.Path(a.out).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'reward':result['reward'],'checks':result['checks'],'output':str(pathlib.Path(a.out).resolve())}),flush=True)
