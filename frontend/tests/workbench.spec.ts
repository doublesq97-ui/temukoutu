import {test,expect,Page} from '@playwright/test';
import path from 'node:path';
const fixture=path.resolve('../tests/fixtures/synthetic/black_white.png');
async function loaded(page:Page) {
  await expect(page.getByRole('button',{name:'生成分割候选',exact:true})).toBeEnabled();
}
async function upload(page:Page,file=fixture) {
  await page.goto('/');await page.getByTestId('upload').setInputFiles(file);await loaded(page);
}
async function id(page:Page) {return page.evaluate(()=>localStorage.getItem('print-extractor-task')!);}
async function alphaAt(page:Page,x:number,y:number) {
  return page.evaluate(async({x,y})=>{
    const task=localStorage.getItem('print-extractor-task');
    const im=new Image();im.src=`/api/tasks/${task}/preview?kind=mask&t=${Date.now()}`;
    await im.decode();const c=document.createElement('canvas');c.width=im.width;c.height=im.height;
    const ctx=c.getContext('2d')!;ctx.drawImage(im,0,0);return ctx.getImageData(x,y,1,1).data[0];
  },{x,y});
}
async function clickPixel(page:Page,x:number,y:number) {
  const canvas=page.getByTestId('editor');const box=(await canvas.boundingBox())!;
  const dims=await canvas.evaluate((c:HTMLCanvasElement)=>({w:c.width,h:c.height}));
  await page.mouse.click(box.x+x*box.width/dims.w,box.y+y*box.height/dims.h);await loaded(page);
}

test('upload → crop → candidates → brush at 200%/400% → undo → RGBA download',async({page})=>{
  const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
  await upload(page);
  await expect(page.getByRole('button',{name:'验证并导出 RGBA PNG ↗',exact:true})).toBeDisabled();
  await expect(page.getByRole('link',{name:'下载透明 PNG ↓'})).toHaveCount(0);
  await page.getByRole('button',{name:'矩形选区',exact:true}).click();
  const canvas=page.getByTestId('editor'),box=(await canvas.boundingBox())!;
  await page.mouse.move(box.x+40,box.y+95);await page.mouse.down();await page.mouse.move(box.x+315,box.y+310,{steps:8});await page.mouse.up();
  await page.getByRole('button',{name:'确认并裁切选区',exact:true}).click();await loaded(page);
  await expect(page.getByRole('button',{name:'验证并导出 RGBA PNG ↗',exact:true})).toBeDisabled();
  await page.getByRole('button',{name:'生成分割候选',exact:true}).click();await loaded(page);
  await expect(page.getByRole('button',{name:'颜色',exact:true})).toBeVisible();
  await expect(page.getByRole('button',{name:'GrabCut',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'颜色',exact:true}).click();await loaded(page);
  for(const bg of ['白底','黑底','棋盘格']) {
    const b=page.getByRole('button',{name:bg,exact:true});await b.click();await expect(b).toHaveAttribute('aria-pressed','true');
  }
  await page.getByRole('button',{name:'200%',exact:true}).click();
  await page.getByRole('button',{name:'添加画笔',exact:true}).click();await clickPixel(page,20,20);
  expect(await alphaAt(page,20,20)).toBe(255);
  await page.getByRole('button',{name:'撤销',exact:true}).click();await loaded(page);expect(await alphaAt(page,20,20)).toBe(0);
  await page.getByRole('button',{name:'重做',exact:true}).click();await loaded(page);expect(await alphaAt(page,20,20)).toBe(255);
  await page.getByRole('button',{name:'400%',exact:true}).click();
  await page.getByRole('button',{name:'擦除画笔',exact:true}).click();await clickPixel(page,20,20);expect(await alphaAt(page,20,20)).toBe(0);
  await page.getByRole('button',{name:'适应',exact:true}).click();
  await page.getByRole('button',{name:'验证并导出 RGBA PNG ↗',exact:true}).click();
  const link=page.getByRole('link',{name:'下载透明 PNG ↓'});await expect(link).toBeVisible();
  const downloadPromise=page.waitForEvent('download');await link.click();const download=await downloadPromise;
  await download.saveAs(path.resolve('../artifacts/browser-export.png'));
  await page.screenshot({path:path.resolve('../artifacts/workbench.png'),fullPage:true});
  await page.reload();await loaded(page);await expect(page.getByRole('link',{name:'下载透明 PNG ↓'})).toBeVisible();
  expect(errors).toEqual([]);
});

test('polygon, supplement/exclude and perspective, then restore original',async({page})=>{
  await upload(page);
  await page.getByRole('button',{name:'多边形',exact:true}).click();
  for(const p of [[70,110],[290,110],[180,310]])await clickPixel(page,p[0],p[1]);
  await page.getByRole('button',{name:'选区排除',exact:true}).click();await loaded(page);expect(await alphaAt(page,180,170)).toBe(0);
  await page.getByRole('button',{name:'多边形',exact:true}).click();
  for(const p of [[70,110],[290,110],[180,310]])await clickPixel(page,p[0],p[1]);
  await page.getByRole('button',{name:'选区补充',exact:true}).click();await loaded(page);expect(await alphaAt(page,180,170)).toBe(255);
  await page.getByRole('button',{name:'四点透视',exact:true}).click();
  for(const p of [[40,50],[300,60],[310,360],[30,350]])await clickPixel(page,p[0],p[1]);
  await page.getByRole('button',{name:'应用四点透视',exact:true}).click();await loaded(page);
  await expect(page.getByText('已应用（重采样）')).toBeVisible();
  await page.getByRole('button',{name:'恢复原图',exact:true}).click();await loaded(page);
  expect((await (await page.request.get(`/api/tasks/${await id(page)}`)).json()).width).toBe(360);
});

test('failed auto segmentation permits manual takeover, deletion and reupload',async({page})=>{
  await upload(page,path.resolve('../tests/fixtures/synthetic/similar_color.png'));
  await page.getByRole('button',{name:'清空选区',exact:true}).click();
  await page.getByRole('button',{name:'生成分割候选',exact:true}).click();await loaded(page);
  await expect(page.getByText('候选蒙版为空',{exact:false})).toBeVisible();
  await page.getByRole('button',{name:'添加画笔',exact:true}).click();await clickPixel(page,180,180);expect(await alphaAt(page,180,180)).toBe(255);
  const task=await id(page);
  await page.getByRole('button',{name:'删除当前任务',exact:true}).click();
  await expect(page.getByRole('button',{name:'选择第一张图片',exact:true})).toBeVisible();
  expect((await page.request.get(`/api/tasks/${task}/preview`)).status()).toBe(404);
  await page.getByTestId('upload').setInputFiles(fixture);await loaded(page);
  expect(await id(page)).not.toBe(task);
});

test('small screen remains usable and invalid upload reports an error',async({page})=>{
  await page.setViewportSize({width:600,height:900});await page.goto('/');
  await page.getByTestId('upload').setInputFiles({name:'invalid.png',mimeType:'image/png',buffer:Buffer.from('not an image')});
  await expect(page.getByRole('alert')).toBeVisible();
  await page.screenshot({path:path.resolve('../artifacts/mobile.png'),fullPage:true});
});

test('brush coordinates after scrolling, pan, and true native comparison zoom',async({page})=>{
  await upload(page);
  await page.getByRole('button',{name:'清空选区',exact:true}).click();
  await page.getByRole('button',{name:'400%',exact:true}).click();
  const editor=page.locator('.editor');
  await editor.evaluate(el=>{el.scrollLeft=300;el.scrollTop=350;});
  await page.getByRole('button',{name:'擦除画笔',exact:true}).click();
  await clickPixel(page,160,180);expect(await alphaAt(page,160,180)).toBe(0);
  expect(await alphaAt(page,190,180)).toBe(255);
  await page.getByRole('button',{name:'拖动画布',exact:true}).click();
  const region=(await editor.boundingBox())!;
  const before=await editor.evaluate(el=>el.scrollLeft);
  await page.mouse.move(region.x+280,region.y+200);await page.mouse.down();
  await page.mouse.move(region.x+220,region.y+160,{steps:4});await page.mouse.up();
  expect(await editor.evaluate(el=>el.scrollLeft)).toBeGreaterThan(before);
  await page.getByLabel('原图缩放').selectOption('2');
  await expect(page.getByAltText('原始商品图')).toHaveJSProperty('width',720);
  await page.getByLabel('结果缩放').selectOption('4');
  expect(await page.getByTestId('result').evaluate(c=>c.getBoundingClientRect().width)).toBe(1440);
});
