import cv2
import numpy as np
from PIL import Image, ImageFilter


def adjust(mask, smooth=0, feather=0, expand=0):
    if not 0 <= smooth <= 10 or not 0 <= feather <= 20 or not -20 <= expand <= 20:
        raise ValueError("边缘参数超出范围")
    a = np.asarray(mask).copy()
    if expand:
        k = np.ones((2*abs(expand)+1,2*abs(expand)+1),np.uint8)
        a = cv2.dilate(a,k) if expand>0 else cv2.erode(a,k)
    if smooth:
        a = cv2.medianBlur(a,2*smooth+1)
    out = Image.fromarray(a)
    return out.filter(ImageFilter.GaussianBlur(feather)) if feather else out
