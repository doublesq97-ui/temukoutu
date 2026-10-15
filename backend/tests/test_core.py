import json
import numpy as np
import pytest
from PIL import Image
from extractor_core import extract
from extractor_core.detection import detect
from extractor_core.transforms import crop,perspective
from extractor_core.segmentation import segment
from extractor_core.export import compose,export_png
from extractor_core.masks import adjust
from tests.synthetic import sample,metrics,CASES


def test_crop_and_polygon():
    image,_=sample()
    result=crop(image,[[30,40],[300,40],[300,350],[30,350]])
    assert result.width in (270,271)
    triangle=crop(image,[[30,40],[300,40],[150,350]])
    assert triangle.getchannel('A').getextrema()==(0,255)
    with pytest.raises(ValueError):crop(image,[[0,0],[1,1],[2,2]])
    with pytest.raises(ValueError):crop(image,[[-10,0],[300,0],[300,350]])


def test_detection_and_perspective():
    image,truth=sample()
    proposal=detect(image)
    assert proposal['status']=='needs_review'
    box=proposal['box'];assert 0<=box[0]<box[2]<=image.width
    result,mask=perspective(image,[[20,20],[330,30],[340,390],[10,380]],truth)
    assert result.size==mask.size
    assert result.width<=image.width
    with pytest.raises(ValueError):perspective(image,[[0,0],[300,300],[0,300],[300,0]])


@pytest.mark.parametrize('method',['color','grabcut','auto','manual'])
def test_source_rgb_and_alpha(tmp_path,method):
    image,truth=sample()
    mask,warnings=segment(image,method)
    assert mask.mode=='L' and warnings
    composed=compose(image,mask)
    assert np.array_equal(np.array(composed)[:,:,:3],np.array(image)[:,:,:3])
    output=tmp_path/(method+'.png')
    info=export_png(image,mask,output,12)
    with Image.open(output) as result:
        assert result.mode=='RGBA'
        assert result.getchannel('A').getextrema()[0]==0
        assert result.getchannel('A').getextrema()[1]==255
    assert info['has_alpha']
    if method!='manual':assert metrics(mask,truth)['iou']>.8


def test_edges_and_empty(tmp_path):
    _,mask=sample()
    adjusted=adjust(mask,1,2,1)
    assert ((np.array(adjusted)>0)&(np.array(adjusted)<255)).any()
    image,_=sample()
    with pytest.raises(ValueError):export_png(image,Image.new('L',image.size),tmp_path/'empty.png')
    with pytest.raises(ValueError):compose(image,Image.new('L',(10,10)))


def test_seed_and_pipeline(tmp_path):
    image,truth=sample()
    input_path=tmp_path/'source.png';output=tmp_path/'out.png';image.save(input_path)
    r=extract(input_path,output,mask=truth)
    assert r['status']=='needs_review' and not r['ai_used']
    mask,_=segment(image,'grabcut',seed=truth)
    assert metrics(mask,truth)['recall']>.99
    with pytest.raises(ValueError):extract(input_path,input_path)
    assert Image.open(input_path).size==image.size


def test_quality_report(tmp_path):
    report={}
    for case in CASES:
        image,truth=sample(case)
        report[case]={}
        for method in ['color','grabcut']:
            mask,_=segment(image,method)
            report[case][method]=metrics(mask,truth)
    path=__import__('pathlib').Path('artifacts/quality-metrics.json')
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(report,indent=2),encoding='utf-8')
    assert report['black_white']['color']['iou']>.8
    assert report['similar_color']['color']['recall']<.5  # Known ambiguity must remain visible.


def test_scaled_export_is_explicit_and_alpha_safe(tmp_path):
    image,mask=sample()
    native=export_png(image,mask,tmp_path/'native.png')
    for scale in [2,4]:
        out=tmp_path/f'x{scale}.png'
        info=export_png(image,mask,out,scale=scale)
        assert (info['width'],info['height'])==(native['width']*scale,native['height']*scale)
        assert info['resampled'] and '不增加原始细节' in info['detail_note']
        with Image.open(out) as result:
            assert result.mode=='RGBA' and result.getchannel('A').getextrema()==(0,255)
            assert result.getpixel((0,0))==(0,0,0,0)
    custom=export_png(image,mask,tmp_path/'custom.png',target_long_edge=1254)
    assert max(custom['width'],custom['height'])==1254
    assert abs(custom['width']/custom['height']-native['width']/native['height'])<.01
    for options in [{'target_long_edge':8},{'scale':3},{'scale':2,'target_long_edge':1254},{'target_long_edge':99999}]:
        with pytest.raises(ValueError):export_png(image,mask,tmp_path/'bad.png',**options)
