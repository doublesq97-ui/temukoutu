from PIL import Image
import numpy as np
from .io import save_png


def compose(image, mask):
    if mask.size != image.size:
        raise ValueError("蒙版尺寸必须匹配工作图像")
    a = np.asarray(image.convert("RGBA")).copy()
    a[:,:,3] = np.minimum(np.asarray(mask.convert("L")), a[:,:,3])
    return Image.fromarray(a)


def export_png(image, mask, output_path, padding=12, scale=1, target_long_edge=None):
    if not 0 <= padding <= 200:
        raise ValueError("透明边距范围为 0–200 像素")
    result = compose(image,mask)
    box = result.getchannel("A").getbbox()
    if box is None:
        raise ValueError("蒙版为空，请先添加需要保留的区域")
    inner = result.crop(box)
    result = Image.new("RGBA",(inner.width+2*padding,inner.height+2*padding))
    result.paste(inner,(padding,padding))
    native_width,native_height = result.size
    if scale not in (1,2,4):
        raise ValueError("导出倍率仅支持 1、2、4")
    if target_long_edge is not None:
        if not isinstance(target_long_edge,int) or target_long_edge < max(result.size):
            raise ValueError("目标长边不能小于原始导出长边")
        if scale != 1:
            raise ValueError("自定义长边不能与倍率同时设置")
        factor = target_long_edge / max(result.size)
    else:
        factor = scale
    size = (round(native_width*factor),round(native_height*factor))
    if max(size)>8192 or size[0]*size[1]>16_000_000:
        raise ValueError("导出最多 8192px 长边且不超过 1600 万像素，请降低倍率")
    resampled = size != result.size
    if resampled:
        # Premultiplied alpha prevents hidden RGB bleeding into transparent edges.
        result = result.convert("RGBa").resize(size,Image.Resampling.LANCZOS).convert("RGBA")
    save_png(output_path,result)
    with Image.open(output_path) as checked:
        checked.load()
        if checked.mode != "RGBA" or checked.getchannel("A").getbbox() is None:
            raise ValueError("PNG Alpha 验证失败")
        extrema = checked.getchannel("A").getextrema()
    return {"width":result.width,"height":result.height,"has_alpha":True,
            "alpha_min":extrema[0],"alpha_max":extrema[1],"content_box":list(box),"padding":padding,
            "native_width":native_width,"native_height":native_height,"resampled":resampled,
            "scale":factor,"detail_note":"插值放大，不增加原始细节" if resampled else "原始像素尺寸，未放大"}
