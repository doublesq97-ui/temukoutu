import io
from PIL import Image,ImageDraw
import pytest
from fastapi.testclient import TestClient
from backend.app.main import create_app
from extractor_core.io import png_bytes
from tests.synthetic import sample


@pytest.fixture
def app(tmp_path):return create_app(tmp_path/'tasks')


@pytest.fixture
def client(app):
    with TestClient(app,base_url='http://127.0.0.1:7860') as c:yield c


def upload(client):
    image,_=sample()
    r=client.post('/api/tasks',files={'file':('fixture.png',png_bytes(image))})
    assert r.status_code==200
    return r.json()['id']


def test_complete_flow(client,app):
    task=upload(client);base='/api/tasks/'+task
    assert client.post(base+'/detect').status_code==200
    for points in [[[30,30],[330,30],[330,380],[30,380]],[[10,10],[280,20],[270,330],[15,340]]]:
        r=client.post(base+('/crop' if points[0][0]==30 else '/transform'),json={'points':points})
        assert r.status_code==200,r.text
    r=client.post(base+'/segment',json={'method':'grabcut'})
    assert r.status_code==200,r.text
    assert len(r.json()['candidates'])==3
    for name in ['color','grabcut','manual']:
        assert client.post(base+'/candidate',json={'name':name}).status_code==200
    work=Image.open(io.BytesIO(client.get(base+'/preview?kind=work').content))
    mask=Image.new('L',work.size)
    ImageDraw.Draw(mask).rectangle((20,20,90,90),fill=255)
    form={'file':('mask.png',png_bytes(mask))}
    assert client.put(base+'/mask',files=form).status_code==200
    assert client.post(base+'/edges',json={'feather':1}).status_code==200
    before=client.get(base).json()
    assert client.post(base+'/history/undo').status_code==200
    assert client.post(base+'/history/redo').json()['rev']==before['rev']
    exported=client.post(base+'/export',json={'padding':8})
    assert exported.status_code==200,exported.text
    output=Image.open(io.BytesIO(client.get(base+'/download').content))
    assert output.mode=='RGBA'
    assert output.getchannel('A').getextrema()==(0,255)
    # New app instance uses persisted task and revisions.
    with TestClient(create_app(app.state.store.root),base_url='http://127.0.0.1:7860') as restarted:
        assert restarted.get(base).json()['rev']==before['rev']
        assert restarted.get(base+'/download').status_code==200
    assert client.post(base+'/history/undo').status_code==200
    assert client.get(base+'/download').status_code==404


def test_failure_takeover_and_reset(client):
    task=upload(client);base='/api/tasks/'+task
    assert client.post(base+'/crop',json={'points':[[0,0],[0,0],[0,0]]}).status_code==422
    assert client.post(base+'/segment',json={'method':'unknown'}).status_code==422
    assert client.post(base+'/segment',json={'method':'manual'}).status_code==200
    assert client.put(base+'/mask',files={'file':('m',png_bytes(Image.new('L',(20,20))))}).status_code==422
    assert client.post(base+'/reset').json()['method']=='unprocessed'


def test_manual_seed_refine(client):
    task=upload(client);base='/api/tasks/'+task
    _,mask=sample()
    assert client.put(base+'/mask',files={'file':('m',png_bytes(mask))}).status_code==200
    assert client.post(base+'/segment',json={'method':'grabcut','use_seed':True}).status_code==200


def test_timeout_is_structured_and_never_commits(client,monkeypatch):
    from concurrent.futures import TimeoutError
    import backend.app.main as main
    task=upload(client);base='/api/tasks/'+task
    rev=client.get(base).json()['rev']
    class Future:
        def result(self,timeout):raise TimeoutError()
        def cancel(self):return True
    class Pool:
        def submit(self,*args):return Future()
    monkeypatch.setattr(main,'POOL',Pool())
    response=client.post(base+'/segment',json={'method':'grabcut'})
    assert response.status_code==504 and 'error' in response.json()
    assert client.get(base).json()['rev']==rev


def test_history_branch_and_limit(client):
    task=upload(client);base='/api/tasks/'+task
    for _ in range(22):
        assert client.post(base+'/edges',json={}).status_code==200
    for _ in range(19):
        assert client.post(base+'/history/undo').status_code==200
    assert client.post(base+'/history/undo').status_code==422
    assert client.get(base).json()['can_redo']
    assert client.post(base+'/edges',json={}).status_code==200
    assert not client.get(base).json()['can_redo']


def test_unprocessed_or_opaque_export_is_not_extraction(client,app):
    task=upload(client);base='/api/tasks/'+task
    response=client.post(base+'/export',json={'padding':12})
    assert response.status_code==422
    assert '尚未提取印花' in response.json()['error']['message']
    # Legacy output with a transparent padding must not remain downloadable.
    store=app.state.store
    from extractor_core.export import export_png
    image,mask,_=store.current(task)
    result=export_png(image,mask,store.path(task)/'output.png',12)
    meta=store.meta(task);meta['export']=result;store.write_meta(task,meta)
    assert client.get(base+'/download').status_code==422
    assert client.post(base+'/segment',json={'method':'manual'}).status_code==200
    response=client.post(base+'/export',json={'padding':12})
    assert response.status_code==422
    assert '没有移除背景' in response.json()['error']['message']
    assert client.post(base+'/segment',json={'method':'grabcut'}).status_code==200
    assert client.post(base+'/export',json={'padding':12}).status_code==200


def test_export_scale_api(client):
    task=upload(client);base='/api/tasks/'+task
    assert client.post(base+'/segment',json={'method':'color'}).status_code==200
    native=client.post(base+'/export',json={}).json()
    enlarged=client.post(base+'/export',json={'scale':4}).json()
    assert enlarged['width']==native['width']*4 and enlarged['resampled']
    custom=client.post(base+'/export',json={'target_long_edge':1254}).json()
    assert max(custom['width'],custom['height'])==1254
    with Image.open(io.BytesIO(client.get(base+'/download').content)) as result:
        assert result.size==(custom['width'],custom['height']) and result.mode=='RGBA'
    assert client.post(base+'/export',json={'scale':3}).status_code==422
    assert client.post(base+'/export',json={'target_long_edge':8}).status_code==422
