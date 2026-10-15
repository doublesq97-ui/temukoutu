export type Point = [number,number];
export function imagePoint(clientX:number,clientY:number,rect:{left:number;top:number;width:number;height:number},width:number,height:number):Point {
  return [Math.max(0,Math.min(width-1,(clientX-rect.left)*width/rect.width)),Math.max(0,Math.min(height-1,(clientY-rect.top)*height/rect.height))];
}
export function rectangle(a:Point,b:Point):Point[] {return [[Math.min(a[0],b[0]),Math.min(a[1],b[1])],[Math.max(a[0],b[0]),Math.min(a[1],b[1])],[Math.max(a[0],b[0]),Math.max(a[1],b[1])],[Math.min(a[0],b[0]),Math.max(a[1],b[1])]];}
