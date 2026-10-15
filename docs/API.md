# 本地 API v0.1.0

基础地址 `http://127.0.0.1:7860`，OpenAPI 文档 `/docs`。仅本机请求，不使用认证或云存储。

成功直接返回 JSON 对象，图像返回 PNG；错误统一为：

```json
{"error":{"code":"invalid_input","message":"蒙版为空，请先添加需要保留的区域"}}
```

| 方法 / 路径 | 输入 | 返回 |
|---|---|---|
| GET /api/health | — | status、app、version、models、ai_used |
| POST /api/tasks | multipart `file` | 任务 id、rev、width、height、method、warnings |
| GET /api/tasks/{id} | — | 当前版本与导出元数据、撤销/重做状态 |
| DELETE /api/tasks/{id} | — | 删除任务全部文件 |
| POST /api/tasks/{id}/detect | — | box `[x0,y0,x1,y1]`、needs_review、warnings |
| POST /api/tasks/{id}/crop | `{"points":[[x,y],...]}` | 裁切新版本；最小 8×8 |
| POST /api/tasks/{id}/transform | 4 个按左上、右上、右下、左下排序的凸四边形点 | 透视后新版本，transformed=true |
| POST /api/tasks/{id}/segment | `{"method":"grabcut","tolerance":28,"use_seed":false}` | 新版本，同时包含 color/grabcut/manual 候选名 |
| POST /api/tasks/{id}/candidate | `{"name":"color"}` | 切换候选并保留其他候选 |
| PUT /api/tasks/{id}/mask | multipart `file`，工作尺寸的灰度 PNG，0 排除、255 保留 | 手动蒙版新版本 |
| POST /api/tasks/{id}/edges | `{"smooth":0,"feather":0,"expand":0}` | 调整边缘后的新版本 |
| POST /api/tasks/{id}/history/undo | — | 上个版本 |
| POST /api/tasks/{id}/history/redo | — | 下个版本 |
| POST /api/tasks/{id}/reset | — | 恢复原图的新版本（可撤销） |
| GET /api/tasks/{id}/preview | kind=result/work/original/mask | PNG；无 kind 默认 result |
| POST /api/tasks/{id}/export | `{"padding":12}` | 导出宽高、Alpha 范围、content_box、warnings、诊断提示 |
| GET /api/tasks/{id}/download | 必须已导出当前版本 | 附件 PNG RGBA |

分割方法 auto/color/grabcut/manual；颜色差异 2–150，平滑 0–10，羽化 0–20px，扩张 -20–20px，边距 0–200px。多边形 3–200 点，坐标属于当前工作图的像素空间，不是 CSS 显示坐标；不能越界或退化。透视后工作图和蒙版尺寸同步变更。

导出扩展参数：`scale` 为 1（默认）、2、4；`target_long_edge` 可指定最终长边（含边距），此时 scale 必须为 1。不允许小于原始导出长边；最多 8192px 长边、1600 万像素。保持纵横比，采用预乘 Alpha Lanczos 插值。返回 `native_width`、`native_height`、`resampled`、`scale`、`detail_note`，明确不增加原始细节。示例：`{"padding":12,"target_long_edge":1254}`。

上传或编辑响应举例：

```json
{"id":"32位十六进制UUID","rev":"版本UUID","width":360,"height":420,
 "method":"grabcut","version":"0.1.0","status":"needs_review","ai_used":false,
 "transformed":false,"can_undo":true,"can_redo":false,
 "candidates":["color","grabcut","manual"],"warnings":["需要人工检查"]}
```

404：任务或导出不存在/已删除；403：非本机来源；413：请求过大；408：上传接收超时；422：格式、几何或参数错误；504：分割计算超时；500：未知处理失败（查看本地日志）。所有路径由服务端构造，无按上传文件名读取任意文件的接口。编辑及撤销使旧导出失效，download 返回 404 直至重新导出。

不将图像 Base64 写入 JSON。数据目录可在启动前用 `PRINT_EXTRACTOR_DATA` 环境变量指定。不要使用多 uvicorn worker 同时写同一目录。
