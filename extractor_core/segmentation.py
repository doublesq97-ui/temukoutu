import cv2
import numpy as np
from PIL import Image

REVIEW = "需要检查：同色印花、阴影、褶皱及细线可能缺失；请用画笔补充或排除。"


def segment(image, method="auto", options=None, seed=None):
    options = options or {}
    if method not in {"auto", "color", "grabcut", "manual"}:
        raise ValueError("可用方法：auto、color、grabcut、manual；P0 不包含模型后端")
    rgb = np.asarray(image.convert("RGB"))
    alpha = np.asarray(image.getchannel("A"))
    h,w = alpha.shape
    if method == "manual":
        return Image.fromarray(alpha.copy()), [REVIEW]
    tolerance = float(options.get("tolerance", 28))
    if not 2 <= tolerance <= 150:
        raise ValueError("颜色差异参数范围为 2–150")
    # Estimate fabric colors from the crop border in perceptual Lab space.
    scale = min(1., 1000 / max(w,h))
    small = cv2.resize(rgb, (max(8,round(w*scale)),max(8,round(h*scale))))
    sh,sw = small.shape[:2]
    lab = cv2.cvtColor(small, cv2.COLOR_RGB2LAB).astype(np.float32)
    band = max(1,min(sh,sw)//24)
    border = np.concatenate([lab[:band].reshape(-1,3),lab[-band:].reshape(-1,3),lab[:,:band].reshape(-1,3),lab[:,-band:].reshape(-1,3)])
    background = np.median(border, axis=0)
    distance = np.linalg.norm(lab-background,axis=2)
    raw = np.clip((distance-tolerance)*255/8,0,255).astype(np.uint8)
    warnings = [REVIEW]
    if method in {"auto", "grabcut"}:
        gc = np.where(raw>127,cv2.GC_PR_FGD,cv2.GC_PR_BGD).astype(np.uint8)
        gc[0,:] = gc[-1,:] = cv2.GC_BGD
        gc[:,0] = gc[:,-1] = cv2.GC_BGD
        gc[distance>tolerance*2] = cv2.GC_PR_FGD
        gc[0,:] = gc[-1,:] = cv2.GC_BGD
        if seed is not None:
            s = cv2.resize(np.asarray(seed), (sw,sh), interpolation=cv2.INTER_NEAREST)
            gc[s==255] = cv2.GC_FGD
            gc[s==0] = cv2.GC_BGD
        if np.any((gc==1)|(gc==3)) and np.any((gc==0)|(gc==2)):
            cv2.setRNGSeed(42)
            cv2.grabCut(small,gc,None,np.zeros((1,65),np.float64),np.zeros((1,65),np.float64),3,cv2.GC_INIT_WITH_MASK)
            raw = np.where((gc==1)|(gc==3),255,0).astype(np.uint8)
        else:
            warnings.append("GrabCut 无法获得前景/背景种子，已退回颜色候选；请手动编辑")
    full = cv2.resize(raw,(w,h),interpolation=cv2.INTER_LINEAR)
    full = np.minimum(full, alpha)
    if not np.any(full):
        warnings.append("候选蒙版为空，可切换手动保留选区后擦除，或使用添加画笔")
    return Image.fromarray(full), warnings
