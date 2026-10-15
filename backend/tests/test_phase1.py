import io
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from backend.app.main import create_app
from extractor_core.io import MAX_BYTES, read_image


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path/'tasks'),base_url='http://127.0.0.1:7860') as c:
        yield c


def encoded(fmt='PNG',size=(80,90)):
    stream=io.BytesIO();Image.new('RGB',size,'white').save(stream,format=fmt);return stream.getvalue()


def test_health(client):
    assert client.get('/api/health').json()['status']=='ok'


@pytest.mark.parametrize('fmt',['JPEG','PNG','WEBP'])
def test_upload_actual_format(client,fmt):
    r=client.post('/api/tasks',files={'file':('../../evil.exe',encoded(fmt),'application/octet-stream')})
    assert r.status_code==200
    task=r.json();assert task['width']==80
    assert client.get('/api/tasks/'+task['id']).status_code==200
    assert client.get('/api/tasks/'+task['id']+'/preview?kind=original').headers['content-type']=='image/png'


@pytest.mark.parametrize('data',[b'broken',b'<svg/>',encoded('GIF'),encoded('PNG')[:35]])
def test_upload_invalid(client,data):
    r=client.post('/api/tasks',files={'file':('x.png',data)})
    assert r.status_code==422
    assert 'error' in r.json()


def test_upload_limits(client):
    r=client.post('/api/tasks',files={'file':('x.png',b'a'*(MAX_BYTES+1))})
    assert r.status_code==422
    assert client.post('/api/tasks',content=b'',headers={'Content-Length':str(MAX_BYTES+2*1024*1024)}).status_code==413
    with pytest.raises(ValueError):read_image(encoded('PNG',(4001,4000)))


def test_chunked_body_limit(client):
    def body():
        for _ in range(28):
            yield b'x'*(1024*1024)
    assert client.post('/api/tasks',content=body(),headers={'Content-Type':'application/octet-stream'}).status_code==413


def test_exif_orientation():
    exif=Image.Exif();exif[274]=6
    stream=io.BytesIO();Image.new('RGB',(80,90)).save(stream,format='JPEG',exif=exif)
    assert read_image(stream.getvalue()).size==(90,80)


def test_local_only_and_missing(client):
    assert client.get('/api/tasks/'+('a'*32)).status_code==404
    assert client.get('/api/health',headers={'Origin':'https://evil.example'}).status_code==403
    assert client.get('/api/health',headers={'Host':'evil.example'}).status_code==403
    assert client.get('/api/health',headers={'Sec-Fetch-Site':'cross-site'}).status_code==403


def test_tasks_independent_delete(client):
    a=client.post('/api/tasks',files={'file':('a',encoded())}).json()['id']
    b=client.post('/api/tasks',files={'file':('b',encoded())}).json()['id']
    assert a!=b
    assert client.delete('/api/tasks/'+a).status_code==200
    for suffix in ['', '/preview','/download']:
        assert client.get('/api/tasks/'+a+suffix).status_code==404
    assert client.get('/api/tasks/'+b).status_code==200
