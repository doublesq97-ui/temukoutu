import cv2
import numpy as np
from PIL import Image, ImageDraw


def polygon_mask(size, points):
    if len(points) < 3 or len(points) > 200:
        raise ValueError("多边形需要 3–200 个点")
    a = np.asarray(points, dtype=np.float32)
    if a.shape != (len(points), 2) or not np.isfinite(a).all():
        raise ValueError("无效坐标")
    if (a < 0).any() or (a[:,0] > size[0]).any() or (a[:,1] > size[1]).any():
        raise ValueError("选区坐标越界")
    if abs(cv2.contourArea(a)) < 4:
        raise ValueError("选区面积太小")
    mask = Image.new("L", size)
    ImageDraw.Draw(mask).polygon([tuple(p) for p in points], fill=255)
    return mask


def crop(image, points):
    mask = polygon_mask(image.size, points)
    a = np.asarray(image).copy()
    a[:,:,3] = np.minimum(a[:,:,3], np.asarray(mask))
    box = mask.getbbox()
    if box[2]-box[0]<8 or box[3]-box[1]<8:
        raise ValueError("裁切结果需至少 8×8 像素")
    return Image.fromarray(a).crop(box)


def perspective(image, points, mask=None):
    polygon_mask(image.size, points)
    if len(points) != 4:
        raise ValueError("透视需要按左上、右上、右下、左下设置四点")
    p = np.float32(points)
    if not cv2.isContourConvex(p):
        raise ValueError("四点必须依次围成凸四边形，不可交叉")
    width = int(max(np.linalg.norm(p[1]-p[0]), np.linalg.norm(p[2]-p[3])))
    height = int(max(np.linalg.norm(p[3]-p[0]), np.linalg.norm(p[2]-p[1])))
    if min(width,height) < 8 or width*height > 16_000_000:
        raise ValueError("透视输出尺寸无效")
    dest = np.float32([[0,0],[width-1,0],[width-1,height-1],[0,height-1]])
    matrix = cv2.getPerspectiveTransform(p,dest)
    result = Image.fromarray(cv2.warpPerspective(np.asarray(image),matrix,(width,height)))
    warped_mask = None if mask is None else Image.fromarray(cv2.warpPerspective(np.asarray(mask),matrix,(width,height)))
    return result, warped_mask
