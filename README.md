# Print Extractor AI

Windows 本地印花提取工作台。上传 T 恤商品照，确认选区，生成候选蒙版，手动修正，导出带真实 Alpha 通道的 PNG。无账号、无 API Key、无云端图片上传、无模型自动下载。

**当前为 P0 半自动工具，所有结果均标为“需要检查”。** 同色印花、黑衣黑描边、褶皱和遮挡无法可靠地从单张照片恢复。程序运行成功不代表图像质量达到商业生产要求。

## 安装和启动

从 GitHub 首次下载或克隆后，请先安装 64 位 Python 3.11（也已在 3.12 验证）及 Node.js 20.19+，双击 **`install.bat`** 安装依赖并构建网页，再双击 **`start.bat`**。本仓库不包含虚拟环境、模型、用户图片和处理结果。

已完成安装的本地工作区可以直接双击 **`start.bat`**，或运行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\start.ps1
```

打开 **http://127.0.0.1:7860**。后端单进程托管已构建的前端，不需要同时启动 Vite。再次启动会复用已运行的应用。关闭浏览器不会关闭服务；双击 `stop.bat` 停止。

复制纯源码到新电脑时，先安装 64 位 Python 3.11（也已在 3.12 验证）及 Node.js 20.19+，然后双击 `install.bat`。安装阶段需要访问 Python/npm 包仓库，运行阶段离线可用。P0 没有模型文件，不会下载 rembg、OCR 或其他模型。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\install.ps1
# 指定 Python：
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\install.ps1 -PythonExe 'C:\Python311\python.exe'
```

安装脚本优先使用本交付目录已准备的 `.runtime` Python 3.11，其他电脑无此目录时使用 PATH 中的 Python。3.11 使用 `backend/requirements-lock311.txt`，3.12 使用 `backend/requirements-lock.txt`；两种环境都已实测。默认服务环境为 `.venv` 的 Python 3.11.15。`.venv312` 是本次开发的 3.12 验证备份，不参与启动。

## 操作流程

首次使用请看 [详细操作步骤与真实商品图实测记录](docs/USER_GUIDE.md)。

1. 拖入或选择 JPG、PNG、WebP。按真实文件内容校验，不依赖扩展名。最大 25MB、1600 万像素，最小 8×8；应用 EXIF 方向后保留原图。
2. 自动候选框仅提供参考。矩形可重画、拖动框内移动、拖动角点调整；多边形逐点点击，Esc 清空。确认后点“确认并裁切选区”。尽量留一小圈衣服供颜色估计，不要把整个衣服作为印花选区。
3. 可选四点透视：依次点击左上、右上、右下、左下，然后应用。可用撤销对照变换前后。透视会重采样，不能修复非平面的褶皱。
4. 选择 GrabCut 或 Lab 颜色差异，调整颜色差异参数后生成候选。按钮可切换颜色、GrabCut 和全保留候选。全保留适合自动失败后人工接管。
5. 使用添加/擦除画笔；笔刷直径以原图像素计。200%/400% 缩放后坐标仍对应真实像素。也可画矩形或多边形后点“选区补充/排除”。每次完整笔划自动保存，也提供“保存当前蒙版”。引导 GrabCut 将当前蒙版纯白/纯黑作为确定种子，半透明像素保持待估计；错误的确定种子也会保留，必要时撤销。
6. 可平滑、羽化、扩张或收缩边缘。每次“应用”都会在当前蒙版上累积，重新调整前可先撤销。最多保留最近 20 步；Ctrl+Z 撤销，Ctrl+Shift+Z 重做，重做分支在新操作后丢弃。
7. 用棋盘格、黑底和白底预览，原图与结果均可放大 200%/400% 并滚动检查。核对文字、细线、装饰、黑白边和残留。
8. 设置透明安全边距，点“验证并导出 RGBA PNG”，再点击下载。默认裁切到 Alpha 非零包围盒并加 12px 透明边距。边距不会放大图案内容；设为 0 时，实心矩形图案可能本身没有 Alpha=0 的像素。

导出后继续编辑会使旧导出失效，必须重新导出。刷新网页会恢复上次任务。重新上传会创建新任务；“恢复原图”可撤销，“删除当前任务”会永久删除该任务及其原图、历史、结果。旧任务不会自动清理，数据全部保存在 `data/tasks/<task_id>/`。停止服务后可自行备份或清理不需要的任务目录。

## 命令行和 Python 接口

在项目根目录运行：

```powershell
.\.venv\Scripts\python.exe -m extractor_core.cli extract --input input.jpg --output output.png --method auto
# 自定义蒙版：
.\.venv\Scripts\python.exe -m extractor_core.cli extract --input input.jpg --output output.png --mask mask.png --method manual --padding 12
# 可复现合成样例：
.\.venv\Scripts\python.exe -m tests.synthetic
.\.venv\Scripts\python.exe -m extractor_core.cli extract --input tests/fixtures/synthetic/black_white.png --output artifacts/example.png --method grabcut
```

```python
from extractor_core import extract
result = extract("input.jpg", "output.png", roi=None, mask=None,
                 method="auto", options={"padding": 12})
```

CLI 和网页都调用同一套 `segmentation.segment`、`transforms`、`masks.adjust`、`export.export_png`。没有第二套抠图算法。`roi` 为工作图坐标多边形，`mask` 为裁切后的工作尺寸的 L 蒙版图或路径；`method` 支持 auto、color、grabcut、manual。auto 是 GrabCut 路径，不是 AI 模型。返回 `needs_review`、尺寸、Alpha 验证、方法、版本和警告；错误以非零退出码和结构化错误返回。

CLI 输出 `output.png`、工作尺寸的 `output.mask.png`、`output.json`。`content_box` 给出导出前的工作坐标裁切边界。输出不得与输入图像或输入蒙版同路径。

导出可选 `--scale 2` / `--scale 4`，或 `--long-edge 1254`（二者互斥）。Python options 对应 `scale` / `target_long_edge`。保持比例和透明通道，最多 8192px 长边、1600 万像素；放大采用插值，不增加原始细节，不进行 AI 重建。默认不放大。

## 验证

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.tmp/pytest-run
npm.cmd run build --prefix frontend
.\.venv\Scripts\python.exe -m tests.synthetic
# 先运行 start.bat；浏览器测试需要本机安装 Google Chrome：
npm.cmd run test:e2e --prefix frontend
# 启动、重复启动、停止、端口冲突、持久化及重启的原生 Windows 集成检查：
.\.venv\Scripts\python.exe scripts/native_smoke.py
```

自动化测试使用合成素材，生成了九类 Ground Truth 蒙版。未提供的三张真实 T 恤图留在 `tests/fixtures/reference/` 待添加，**未声称真实照片验收通过**。实际结果见 [测试报告](docs/TEST_REPORT.md)、[架构](docs/ARCHITECTURE.md)、[API](docs/API.md) 和 [后续计划](docs/NEXT_STEPS.md)。

开发模式（需要时）：后端用 `python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 7860`，前端用 `npm.cmd run dev --prefix frontend`。Vite 仅监听 127.0.0.1:5173，通过代理访问后端，不开放跨网来源。

## 排错

| 现象 | 处理 |
|---|---|
| 缺少环境或前端构建 | 运行 install.bat；不要直接复制另一电脑的虚拟环境 |
| 7860 被其他程序占用 | 关闭占用程序再启动；脚本不会擅自结束其他程序 |
| 启动失败 | 查看 artifacts/server.err.log；批处理窗口保留错误 |
| 超时或预览慢 | 缩小选区；分割内部最多 1000px 工作边长，回映射到工作尺寸；16MP 全图画笔仍可能较慢 |
| 候选全空或选到衣服 | 重画胸前选区、调整参数、切换算法；使用全保留后擦除，或添加画笔 |
| 黑描边缺失 | 与衣服同色的原始信息不可辨；人工补蒙版只能保留照片已有像素，不能恢复真实设计颜色 |
| 近似背景色没有结果 | 默认为空也允许手工添加，不导出空蒙版 |
| 模型/AI 未使用 | P0 有意使用 CPU 传统方法；未实现 rembg 插件，不会自动下载 |
| Stop 无法读取进程信息 | 需要普通 Windows WMI/CIM 可用；在任务管理器核对本应用 uvicorn 命令后关闭 |
| pytest 在受限自动化沙箱阻塞 | Windows asyncio 需要本地 socketpair 权限；本次原生权限测试通过，普通本机终端不受此沙箱限制 |

本工具仅监听 127.0.0.1。原图 RGB 不被重绘；蒙版编辑只改变 Alpha。透视操作会进行几何重采样。没有超分辨率、SVG、批处理、OCR、衣服褶皱复原或商业级自动提取承诺。
