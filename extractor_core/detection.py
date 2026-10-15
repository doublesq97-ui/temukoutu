import cv2
import numpy as np


def detect(image):
    """Color contrast + texture + central prior; a proposal, never a semantic claim."""
    rgb = np.asarray(image.convert("RGB"))
    h, w = rgb.shape[:2]
    scale = min(1, 800 / max(w, h))
    small = cv2.resize(rgb, (max(8, round(w * scale)), max(8, round(h * scale))))
    sh, sw = small.shape[:2]
    lab = cv2.cvtColor(small, cv2.COLOR_RGB2LAB).astype(np.float32)
    border = np.concatenate([lab[:max(1, sh//12)].reshape(-1,3), lab[-max(1,sh//12):].reshape(-1,3)])
    contrast = np.linalg.norm(lab - np.median(border, axis=0), axis=2)
    gray = cv2.cvtColor(small, cv2.COLOR_RGB2GRAY)
    edges = cv2.GaussianBlur(cv2.Canny(gray, 40, 120).astype(np.float32), (0,0), 5)
    yy, xx = np.mgrid[:sh, :sw]
    prior = np.exp(-(((xx/sw-.5)/.32)**2 + ((yy/sh-.43)/.32)**2))
    score = (contrast / 160 + edges / 70) * prior
    active = (score > max(.15, float(np.percentile(score, 78)))).astype(np.uint8)
    active[:sh//10] = 0
    active[sh*9//10:] = 0
    active[:, :sw//10] = 0
    active[:, sw*9//10:] = 0
    ys, xs = np.where(active)
    if len(xs) < 20:
        box = [round(w*.2), round(h*.2), round(w*.8), round(h*.75)]
        reason = "没有稳定的纹理候选，已给出中心参考框，请手动调整"
    else:
        pad = max(5, round(min(sw,sh)*.03))
        box = [max(0, round((xs.min()-pad)/scale)), max(0,round((ys.min()-pad)/scale)),
               min(w, round((xs.max()+pad+1)/scale)), min(h,round((ys.max()+pad+1)/scale))]
        reason = "颜色/边缘/中心先验候选，可能包含衣服；请确认选区"
    return {"box": box, "status": "needs_review", "warnings": [reason]}
