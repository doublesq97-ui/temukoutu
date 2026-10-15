# P0 测试报告

## 原图提取的可选插值放大

用户选择保留原图提取、不增加原始细节的放大模式后，增加 1/2/4 倍和自定义长边导出。新增 2 项核心/API 测试通过，验证倍率、比例、参数上限、透明通道和元数据标识；生产构建通过。真实商品浏览器场景验证自定义长边 1254，下载文件 1018×1254，Pillow 重新打开为 RGBA、Alpha 0–255。文件为 `artifacts/real-product-1254-interpolated.png`，独立记录 `artifacts/upscale-verification.json`。该文件是插值放大，不是原生高清或 AI 重建。

## 2026-10-15 用户反馈修复：未提取也可下载

真实用户最新两个任务处于 unprocessed，但旧版仍允许把原图加透明边距后导出；PNG 格式和 Alpha 合法并不代表衣服背景已被移除。修复后，前端在未处理/仅裁切时禁用导出，隐藏旧下载；后端在导出和下载两条入口同时验证状态及内容 Alpha，拒绝全不透明工作图。透明边距不参与该验证。

新增 API 回归覆盖未处理、旧版已导出的遗留文件、手动全保留、正常分割导出；7 项集成测试通过。浏览器回归追加上传后/仅裁切后禁用导出断言。

本次用户实际上传的 Family Christmas 2026 商品图已用于候选检查：颜色差异法比默认 GrabCut 保留了更多绿色装饰与鹿角；输出仍需检查深色边线。该真实图没有 GT，不计算 IoU，也不视为任务书其他两张参考图已提供。

日期：2026-10-15。版本：0.1.0。结论：**本地半自动工作流功能验收通过；指定真实商品图的质量验收待原图提供。**

## 实测环境

- 原生 Windows 11，`Windows-11-10.0.26200-SP0`，64 位。
- 默认 Python 3.11.15（项目内 uv 管理运行时），已通过正式安装脚本创建 `.venv`。
- 额外验证 Python 3.12.10；没有修改系统 Python。
- Node.js 24.14.0，npm 11.9.0，Vite 6.4.4，TypeScript 5.7.3，React 19。
- CPU 图像后端：OpenCV 4.14.0、Pillow 12.3.0；NumPy 3.11 环境 2.4.6、3.12 环境 2.5.4。
- 使用本机安装的 Chrome 进行无头浏览器测试；不下载浏览器或图像模型。
- GPU 型号查询受最初沙箱 CIM 权限限制，未用于处理；未声称完成 GPU 验证。

## 实际命令与结果

| 阶段 | 命令 | 结果 |
|---|---|---|
| Phase 1 | `.venv/Scripts/python.exe -m pytest backend/tests/test_phase1.py -q` | 初始 12 passed；最终加入 chunked 限制共 13 个案例 |
| Phase 2 | `.venv/Scripts/python.exe -m pytest backend/tests/test_core.py -q` | 9 passed，包含 9 类图案 × 2 方法的指标生成 |
| Phase 3 | `npm.cmd run build --prefix frontend` | TypeScript + Vite production build 通过，31 modules |
| Phase 3/5 | `npm.cmd run test:e2e --prefix frontend` | 最终 5 passed，16.7s |
| Phase 4 | `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/install.ps1` | 默认 Python 3.11 安装依赖、npm ci、构建、核心导入全部成功 |
| Phase 4 | `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/start.ps1 -NoBrowser` | 实际监听 127.0.0.1:7860，健康接口及页面 HTTP 200 |
| Phase 5 | `.venv/Scripts/python.exe -m pytest -q --basetemp=.tmp/pytest-primary --junitxml=artifacts/pytest-primary.xml` | 全量 26 passed，11.04s |
| Phase 5 补测 | 两个新增 API 案例：超时无提交、20 步历史/分支 | 2 passed，2.33s；共 28 个不同 Python 案例已通过 |
| 版本交叉验证 | `.venv311/Scripts/python.exe -m pytest -q` | 26 passed，19.30s |
| 版本交叉验证 | 当时的 Python 3.12 `.venv/Scripts/python.exe -m pytest -q` | 26 passed，16.57s；后改名为 .venv312 保留 |
| 原生集成 | `.venv/Scripts/python.exe scripts/native_smoke.py` | 6 项检查全 true，报告 native-smoke.json |
| 依赖一致性 | `.venv/Scripts/python.exe -m pip check` | No broken requirements found |
| CLI | `.venv/Scripts/python.exe -m extractor_core.cli extract --input tests/fixtures/synthetic/black_white.png --output artifacts/cli-export.png --method auto` | needs_review，154×116，RGBA，Alpha 0–255，PNG/蒙版/JSON 已落盘 |

上述测试的完整可复制命令见 README。新增两个 API 测试可单独运行：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/integration/test_api_flow.py::test_timeout_is_structured_and_never_commits tests/integration/test_api_flow.py::test_history_branch_and_limit -q --basetemp=.tmp/pytest-extra --junitxml=artifacts/pytest-extra.xml
```

所有测试可通过 README 的全量命令重新执行。最终代码共 28 个 Python 测试案例，5 个浏览器场景，6 项原生启停检查。全量 26 与补测 2 的报告分别保留，没有将不同 Python 版本重复计为独立功能案例。

## 功能覆盖

| 能力 | 证据 |
|---|---|
| JPG / PNG / WebP 内容校验、错误格式、损坏文件 | test_phase1 参数化上传用例 |
| 25MB / 16MP 限制、分块请求限制 | upload_limits、chunked_body_limit |
| EXIF 旋转与原图独立保留 | exif_orientation、任务 original.png |
| 自动候选、矩形、多边形裁切 | 核心 detection/crop + 浏览器矩形拖选、多边形操作 |
| 透视、变换前后恢复 | 核心凸四点测试 + 浏览器四点变换/恢复原图 |
| 两种候选及手动全保留 | source_rgb_and_alpha、complete_flow、浏览器候选切换 |
| 画笔添加/擦除、选区补充/排除 | 浏览器回读服务端蒙版像素 0/255 |
| 200% / 400% 后坐标正确 | 浏览器缩放画笔 + 滚动画布后像素回读及相邻像素检查 |
| 原图、结果局部放大和拖动 | 浏览器真实宽度 720/1440px 校验 + pan 后滚动偏移 |
| 平滑、羽化、扩张 | 核心中间 Alpha 测试 + API edges |
| Undo / Redo 与历史上限 | 浏览器画笔前后像素、API 20 步/新分支补测 |
| 黑/白/棋盘格 | 浏览器切换并检查按钮状态，截图可见棋盘格 |
| RGBA 导出、安全边距、空蒙版拒绝 | Pillow mode/Alpha、单元测试、浏览器真实下载 |
| 自动失败后人工继续 | similar_color 空候选后添加画笔并保存 |
| 删除后不能访问文件 | API 独立任务与原生 preview 404 |
| 重启与持久化 | 新 app 对象恢复 + 实际进程停止重启后 revision/download 保留 |
| 超时与错误提示 | 模拟超时返回结构化 504，不提交 revision；无效上传网页显示 alert |
| 小屏布局 | 600×900 浏览器场景，截图 mobile.png |
| 本地绑定与来源限制 | 本机 origin/host/cross-site 403 测试；启动参数固定 127.0.0.1 |
| 重复启动/停止/端口冲突 | 原生脚本检查实例 PID 不变，停止释放端口，其他服务占用时拒绝 |

P0 十项功能门槛均有相应验证：网页打开、上传选区、双候选及交互、三背景、有效 Alpha、完整下载、人工接管、后端测试、前端构建、README 安装操作排错。

## 图像质量（仅合成 Ground Truth）

合成过程见 `tests/synthetic.py`，图像和已知真值蒙版分别保存，不将网络图冒充用户素材。指标将预测及真值 Alpha >127 二值化计算。表中是比例值，不是实际商品图的准确率承诺。完整 Precision/Recall/IoU 在 `artifacts/quality-metrics.json`。

| 合成场景 | 颜色 IoU | GrabCut IoU | 观察 |
|---|---:|---:|---|
| 黑衣白字 | 0.9141 | 0.9203 | 高对比主体可提取，边缘仍有差异 |
| 黑衣彩字 | 0.9266 | 0.9261 | 彩色主体可提取 |
| 黑衣、与衣服同色的黑描边 | 0.4258 | 0.4229 | 描边无法从同色布料中可靠恢复，明显漏选 |
| 白衣深字 | 0.9215 | 0.9222 | 高对比主体可提取 |
| 复杂彩色图案 | 0.9580 | 0.9729 | 当前合成组合表现较好，不可外推真实复杂商品 |
| 渐变/阴影 | 0.9099 | 0.8990 | 阴影和过渡边缘有遗漏 |
| 平面透视 | 0.8381 | 0.8516 | 重采样边缘与原始 Alpha 存在差异 |
| 局部褶皱 | 0.8897 | 0.8149 | 不能恢复非平面真实设计 |
| 近似背景色 | 0.0000 | 0.0000 | 默认参数自动失败，人工流程已验证可继续 |

高对比合成样例 Recall 为 1.0；黑描边 Recall 分别约 0.4258/0.4229；近似背景色 Recall 为 0。所有算法始终返回需检查。候选定位也不是语义印花识别。

## 持久产物

- `artifacts/pytest-primary.xml`、`pytest-extra.xml`、`pytest311-results.xml`、`pytest-results.xml`
- `artifacts/playwright-results.json`、`native-smoke.json`、`quality-metrics.json`
- `artifacts/workbench.png`、`mobile.png`：实际浏览器页面截图，已查看工作台截图。
- `artifacts/browser-export.png`：浏览器实际下载，177×156，Pillow RGBA，Alpha 0–255。
- `artifacts/cli-export.png` / `.mask.png` / `.json`：CLI 实际结果。
- `artifacts/native-export.png`：原生服务 API 实际导出。
- `backend/requirements-lock311.txt` / `requirements-lock.txt`、`frontend/package-lock.json`：实测依赖。

`artifacts/` 为可再生结果目录，已忽略版本管理；本次交付工作区保留文件。

## 缺失素材、限制和已知问题

1. Christmas 2026、Thanksgiving 2026、Ain't No Family Like The One I Got 三张原图未提供，预留 `tests/fixtures/reference/`。三张图的完整文字、装饰、细线、残留和边缘人工质量检查均未执行，没有虚构 IoU。
2. 相似色和黑描边质量不足；“半自动功能验收通过”不等于“商业级图像质量通过”。不恢复遮挡像素，不进行重绘或超分辨率。
3. 背景残留提示是工作边界启发式，不能找出所有内部残留。复杂纹理衣服、反光、阴影和紧贴选区的图案仍需人工检查。
4. 大图画笔会对完整图像进行组合，16MP 交互速度未做压力基准；历史图像会占用较多磁盘。没有自动过期清理、任务列表和跨进程锁。
5. 超时线程不能立即强杀，但其计算是纯函数，不会晚到覆盖任务；P1 改独立进程。45 秒超时由可控测试替身触发，未故意挂起实际 OpenCV 来占用机器。
6. 模型后端 rembg 为任务书可选项，P0 未安装；界面明确 AI 未使用。没有 OCR 或自动语义质量评分。
7. 测试依赖的 Starlette 输出 httpx TestClient 弃用警告，测试均通过；运行时 API 不依赖该测试客户端。
8. 启停依赖正常 Windows WMI/CIM 读取进程信息；已在本机原生权限实测。初始受限沙箱的 socketpair/realpath 限制曾阻止测试和构建，改在原生权限运行成功，未把受限运行冒充通过。

修复记录：Vite CSS 导入、CLI 根解析器、Windows venv 子进程停止、原图真实像素倍率、分块上传上限、CLI 原图覆盖保护、CLI UTF-8 输出、原生测试后台输出管道等待。未自动发布 GitHub、部署网站或上传图片。
