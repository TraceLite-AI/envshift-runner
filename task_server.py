"""Local-only task server and artifact storage, shared by manual/GUI validation."""
import base64,copy,http.server,json,pathlib,threading,urllib.parse
from task_world import fixture,apply,grade,TITLES

class TaskSession:
    def __init__(self,task,out):
        self.task=task;self.out=pathlib.Path(out);self.out.mkdir(parents=True,exist_ok=True);self.lock=threading.Lock();self.reset()
        owner=self;root=pathlib.Path(__file__).resolve().parent
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def reply(self,data,ctype='application/json',code=200,headers=None):
                self.send_response(code);self.send_header('Content-Type',ctype);self.send_header('Cache-Control','no-store')
                for k,v in (headers or {}).items():self.send_header(k,v)
                self.end_headers();self.wfile.write(data)
            def do_GET(self):
                path=urllib.parse.urlparse(self.path).path
                if path=='/api/state':
                    with owner.lock:data=json.dumps(owner.state).encode()
                    return self.reply(data)
                if path=='/probe':
                    import scroll_probe
                    return self.reply(scroll_probe.HTML.encode(),'text/html; charset=utf-8')
                if path in ['/app.js','/app.css']:return self.reply((root/path[1:]).read_bytes(),'text/javascript' if path.endswith('.js') else 'text/css')
                if path.startswith('/export/'):
                    name=urllib.parse.unquote(path[8:])
                    with owner.lock:
                        if name not in owner.state.get('exports',{}):return self.reply(b'Not found','text/plain',404)
                        data=(owner.out/'exports'/name).read_bytes()
                    return self.reply(data,'application/octet-stream',headers={'Content-Disposition':'attachment; filename="'+name+'"'})
                if path!='/':return self.reply(b'Not found','text/plain',404)
                html='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+TITLES[owner.task]+'</title><link rel="stylesheet" href="/app.css"><header>'+TITLES[owner.task]+'</header><nav id="nav"></nav><main><div id="app"></div></main><script>const TASK='+json.dumps(owner.task)+';</script><script src="/app.js"></script></html>'
                return self.reply(html.encode(),'text/html; charset=utf-8')
            def do_POST(self):
                if self.path!='/api/action':return self.reply(b'Not found','text/plain',404)
                try:
                    action=json.loads(self.rfile.read(int(self.headers.get('Content-Length',0))))
                    with owner.lock:
                        fresh=copy.deepcopy(owner.state);apply(owner.task,fresh,action)
                        if owner.task=='G23' and action['op']=='export':
                            dest=owner.out/'exports';dest.mkdir(exist_ok=True);(dest/action['name']).write_bytes(base64.b64decode(fresh['exports'][action['name']],validate=True))
                        owner.state=fresh;owner.audit.append(copy.deepcopy(action));data=json.dumps(owner.state).encode()
                    self.reply(data)
                except Exception as e:self.reply(json.dumps({'error':str(e) or type(e).__name__}).encode(),code=400)
        self.server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.url=f'http://127.0.0.1:{self.server.server_port}/'
    def reset(self):
        with self.lock:
            self.state=fixture(self.task);self.audit=[]
            if self.task=='G23':
                (self.out/'source.png').write_bytes(base64.b64decode(self.state['source_png']))
                for p in (self.out/'exports').glob('*') if (self.out/'exports').exists() else []:
                    if p.is_file():p.unlink()
    def result(self):
        with self.lock:
            state=copy.deepcopy(self.state);result=grade(self.task,state)
            if self.task=='G23':
                p=self.out/'exports/badge.png';value=state.get('exports',{}).get('badge.png')
                result['checks']['export_file_matches_saved_delivery']=bool(value) and p.is_file() and p.read_bytes()==base64.b64decode(value)
                result['checks']['source_file_unchanged']=(self.out/'source.png').read_bytes()==base64.b64decode(fixture('G23')['source_png'])
                result['reward']=int(all(result['checks'].values()))
            return {**result,'state':state,'audit':copy.deepcopy(self.audit)}
    def close(self):self.server.shutdown();self.server.server_close();self.thread.join(timeout=3)
