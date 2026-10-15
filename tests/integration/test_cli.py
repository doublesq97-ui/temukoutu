import json
import subprocess
import sys
from PIL import Image
from tests.synthetic import sample


def test_real_cli(tmp_path):
    image,_=sample();src=tmp_path/'input.png';out=tmp_path/'output.png';image.save(src)
    result=subprocess.run([sys.executable,'-m','extractor_core.cli','extract','--input',str(src),'--output',str(out),'--method','auto'],capture_output=True,text=True,encoding='utf-8',env={**__import__('os').environ,'PYTHONIOENCODING':'utf-8'},timeout=30)
    assert result.returncode==0,result.stderr
    metadata=json.loads(result.stdout)
    assert metadata['has_alpha'] and metadata['status']=='needs_review'
    assert Image.open(out).mode=='RGBA'
    assert out.with_suffix('.json').exists()
    assert (tmp_path/'output.mask.png').exists()
