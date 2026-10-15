"""Run in a native Windows terminal, from project root. Leaves the app running."""
import io
import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

import httpx
from PIL import Image
from extractor_core.io import png_bytes
from tests.synthetic import sample

BASE='http://127.0.0.1:7860'


def script(name,*args,expected=0):
    log=ROOT/'.tmp'/('native-'+name+'.log')
    log.parent.mkdir(exist_ok=True)
    print('Checking '+name,flush=True)
    # A detached Windows service can inherit pipe handles. Use a file so the
    # test never waits for the background service to close a captured pipe.
    with log.open('w',encoding='utf-8') as stream:
        result=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts'/name),*args],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,timeout=45)
    output=log.read_text(encoding='utf-8',errors='replace')
    if (result.returncode==0)!=(expected==0):
        raise AssertionError(output)
    return output


def main():
    if sys.platform!='win32':
        raise SystemExit('This test requires native Windows; no Windows pass is inferred elsewhere.')
    report={'platform':sys.platform,'python':sys.version.split()[0],'checks':{}}
    script('start.ps1','-NoBrowser')
    pid=(ROOT/'artifacts/server.pid').read_text().strip()
    script('start.ps1','-NoBrowser')
    assert (ROOT/'artifacts/server.pid').read_text().strip()==pid
    report['checks']['repeated_start_single_instance']=True
    with httpx.Client(base_url=BASE,trust_env=False,timeout=30) as client:
        assert client.get('/api/health').json()['status']=='ok'
        assert client.get('/').status_code==200
        image,_=sample()
        r=client.post('/api/tasks',files={'file':('native.png',png_bytes(image))});r.raise_for_status()
        task=r.json()['id'];base='/api/tasks/'+task
        r=client.post(base+'/segment',json={'method':'grabcut'});r.raise_for_status()
        r=client.post(base+'/export',json={'padding':12});r.raise_for_status()
        output=client.get(base+'/download');output.raise_for_status()
        im=Image.open(io.BytesIO(output.content));im.load()
        assert im.mode=='RGBA' and im.getchannel('A').getextrema()==(0,255)
        report['checks']['live_upload_export_rgba']=True
        (ROOT/'artifacts/native-export.png').write_bytes(output.content)
        rev=client.get(base).json()['rev']
    script('stop.ps1')
    try:
        httpx.get(BASE+'/api/health',trust_env=False,timeout=2)
    except httpx.TransportError:
        report['checks']['stop_releases_port']=True
    else:
        raise AssertionError('stop left a service alive')

    class OtherService(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200);self.end_headers();self.wfile.write(b'{}')
        def log_message(self,*args):
            pass
    other=HTTPServer(('127.0.0.1',7860),OtherService)
    thread=threading.Thread(target=other.serve_forever,daemon=True);thread.start()
    try:
        result=script('start.ps1','-NoBrowser',expected=1)
        report['checks']['occupied_port_rejected']=True
    finally:
        other.shutdown();other.server_close();thread.join(timeout=3)
    script('start.ps1','-NoBrowser')
    with httpx.Client(base_url=BASE,trust_env=False,timeout=10) as client:
        assert client.get(base).json()['rev']==rev
        assert client.get(base+'/download').status_code==200
        assert client.delete(base).status_code==200
        assert client.get(base+'/preview').status_code==404
    report['checks']['restart_preserves_task_and_export']=True
    report['checks']['delete_removes_access']=True
    (ROOT/'artifacts/native-smoke.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
