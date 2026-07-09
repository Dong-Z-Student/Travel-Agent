# Travel-Agent 运行与脚本手册

本文档用于记录项目常用启动命令、数据脚本运行方式、接口检查方法。命令默认在 Windows PowerShell 下执行。

## 1. 环境文件

前端环境文件位于项目根目录：

```powershell
E:\大三下\WebGIS\智游图策\Travel-Agent\.env
```

可参考：

```powershell
E:\大三下\WebGIS\智游图策\Travel-Agent\.env.example
```

常用字段：

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_TIANDITU_KEY=
VITE_SUPABASE_URL=
VITE_SUPABASE_ANON_KEY=
```

后端环境文件位于：

```powershell
E:\大三下\WebGIS\智游图策\Travel-Agent\backend\.env
```

可参考：

```powershell
E:\大三下\WebGIS\智游图策\Travel-Agent\backend\.env.example
```

后端常用必填项：

```env
DATABASE_URL=
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_JWT_SECRET=
AMAP_WEB_SERVICE_KEY=
DEEPSEEK_API_KEY=
```

说明：

- `DATABASE_URL` 用于 SQLAlchemy 连接 Supabase Postgres。
- `SUPABASE_SERVICE_ROLE_KEY` 用于服务端写入 Supabase Storage、用户资料等服务端操作。
- `AMAP_WEB_SERVICE_KEY` 用于高德 POI、天气、路线规划。
- `DEEPSEEK_API_KEY` 用于 LangGraph Agent 调用模型。
- 环境变量文件不要提交到 Git。

## 2. 启动后端

推荐在 `backend` 目录下启动后端：

```powershell
cd E:\大三下\WebGIS\智游图策\Travel-Agent\backend
python -m uvicorn app.main:app --reload
```

启动成功后会看到类似输出：

```text
Uvicorn running on http://127.0.0.1:8000
Application startup complete.
```

后端接口文档：

```text
http://127.0.0.1:8000/docs
```

健康检查接口：

```text
http://127.0.0.1:8000/api/health
```

PowerShell 检查方式：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

正常返回：

```json
{
  "status": "ok"
}
```

注意：

- 不建议在项目根目录直接运行 `python -m uvicorn app.main:app --reload`，因为 `app` 包在 `backend` 目录下，根目录运行可能出现 `ModuleNotFoundError: No module named 'app'`。
- 如果要从根目录启动，需要显式调整 Python 路径或使用封装脚本，但日常开发建议直接进入 `backend` 后启动。

## 3. 启动前端

在项目根目录执行：

```powershell
cd E:\大三下\WebGIS\智游图策\Travel-Agent
npm install
npm run dev
```

启动成功后默认访问：

```text
http://localhost:5173
```

前端构建检查：

```powershell
npm run build
```

本地预览构建结果：

```powershell
npm run preview
```

说明：

- 前端会通过 `VITE_API_BASE_URL` 调用后端，默认是 `http://localhost:8000`。
- 日常联调时通常需要先启动后端，再启动前端。

## 4. 常用接口检查

后端启动后，可以通过 Swagger 页面检查接口：

```text
http://127.0.0.1:8000/docs
```

常用检查项：

```text
GET  /api/health
GET  /api/pois
GET  /api/weather
POST /api/spatial-query/nearby
POST /api/routes/plan
POST /api/agent/chat
```

如果前端地图没有显示真实 POI，优先检查：

1. 后端是否启动。
2. 前端 `.env` 中 `VITE_API_BASE_URL` 是否指向 `http://localhost:8000`。
3. 浏览器 F12 Network 中 `/api/pois` 是否为 200。
4. Supabase 数据库中是否已有 POI 数据。

如果 Agent 不回复或回复保底内容，优先检查：

1. 后端 `.env` 中 `DEEPSEEK_API_KEY` 是否配置。
2. 后端 `.env` 中 `AMAP_WEB_SERVICE_KEY` 是否配置。
3. 后端日志是否有模型调用、工具调用或数据库连接错误。
4. `/api/agent/chat` 的响应中 `tool_trace_summary` 是否有 failed 项。

## 5. 数据脚本

所有数据脚本都建议在 `backend` 目录下执行：

```powershell
cd E:\大三下\WebGIS\智游图策\Travel-Agent\backend
```

### 5.1 采集高德 POI 并入库

脚本：

```powershell
python scripts/fetch_amap_pois.py
```

推荐显式指定城市和类别：

```powershell
python scripts/fetch_amap_pois.py --city 武汉市 --categories scenic_spot,hotel,metro_station --max-pages 1
```

只采集景点：

```powershell
python scripts/fetch_amap_pois.py --city 武汉市 --categories scenic_spot --max-pages 1
```

只采集酒店：

```powershell
python scripts/fetch_amap_pois.py --city 武汉市 --categories hotel --max-pages 1
```

只采集地铁站：

```powershell
python scripts/fetch_amap_pois.py --city 武汉市 --categories metro_station --max-pages 1
```

小规模 dry-run 检查，不写数据库：

```powershell
python scripts/fetch_amap_pois.py --city 武汉市 --categories scenic_spot --max-pages 1 --dry-run
```

常用参数：

```text
--city             传给高德的城市名，建议显式传 武汉市
--categories       POI 类别，支持 scenic_spot, hotel, metro_station
--max-pages        每个关键词最多请求页数
--offset           每页数量，高德该接口通常最多 25
--delay-seconds    请求间隔
--retries          单次请求重试次数
--retry-interval   重试间隔
--timeout          请求超时时间
--dry-run          只抓取和清洗，不写入数据库
```

正常返回示例：

```json
{
  "job_id": "xxx",
  "total_raw_count": 25,
  "raw_inserted_count": 25,
  "clean_count": 25,
  "poi_inserted_count": 25,
  "poi_updated_count": 0,
  "failed_count": 0,
  "errors": []
}
```

依赖环境变量：

```env
DATABASE_URL=
AMAP_WEB_SERVICE_KEY=
```

### 5.2 导入景点图文资料

脚本：

```powershell
python scripts/import_scenic_profiles.py
```

默认读取：

```text
backend/data/scenic_profiles/scenic_profiles.csv
```

默认图片目录：

```text
backend/data/scenic_profiles/images/
```

推荐先 dry-run：

```powershell
python scripts/import_scenic_profiles.py --dry-run
```

确认无误后正式导入：

```powershell
python scripts/import_scenic_profiles.py
```

指定 CSV：

```powershell
python scripts/import_scenic_profiles.py --csv-path data/scenic_profiles/scenic_profiles.csv
```

指定 Supabase Storage bucket：

```powershell
python scripts/import_scenic_profiles.py --bucket scenic-images
```

CSV 表头当前约定：

```csv
amap_poi_id,name_en,short_intro_zh,full_description_zh,recommended_duration_minutes,opening_hours,ticket_info,image_path,image_caption
```

`image_path` 建议填写相对路径，例如：

```csv
images/八七会议.jpg
```

正常返回示例：

```json
{
  "csv_path": "...",
  "total_rows": 25,
  "matched_pois": 25,
  "missing_pois": 0,
  "profiles_inserted": 0,
  "profiles_updated": 25,
  "images_inserted": 0,
  "images_updated": 19,
  "images_uploaded": 19,
  "url_images_used": 0,
  "skipped_images": 6,
  "errors": []
}
```

依赖环境变量：

```env
DATABASE_URL=
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
```

### 5.3 验证 Agent 工具封装

脚本：

```powershell
python scripts/verify_agent_tools.py
```

建议显式指定天气区县：

```powershell
python scripts/verify_agent_tools.py --district 洪山区
```

如果也要验证高德路线规划：

```powershell
python scripts/verify_agent_tools.py --district 洪山区 --plan-route
```

该脚本会检查：

- POI 搜索工具。
- POI 详情工具。
- 附近酒店工具。
- 附近地铁工具。
- 人口热力摘要工具。
- 天气工具。
- 可选的路线规划工具。

依赖环境变量：

```env
DATABASE_URL=
AMAP_WEB_SERVICE_KEY=
```

如果启用路线规划，还需要确保高德 Web 服务 Key 有路线规划接口权限。

## 6. 推荐联调顺序

第一次完整联调建议按下面顺序：

```powershell
cd E:\大三下\WebGIS\智游图策\Travel-Agent\backend
python -m uvicorn app.main:app --reload
```

新开一个 PowerShell：

```powershell
cd E:\大三下\WebGIS\智游图策\Travel-Agent
npm run dev
```

然后依次检查：

1. 打开 `http://127.0.0.1:8000/api/health`，确认后端健康。
2. 打开 `http://127.0.0.1:8000/docs`，确认 Swagger 正常。
3. 打开 `http://localhost:5173`，确认地图加载。
4. F12 Network 检查 `/api/pois` 是否 200。
5. 点击 POI，确认简介和图片正常。
6. 使用 Agent 提问，检查 `/api/agent/chat` 是否 200。
7. 如果 Agent 触发地图路线，检查地图上是否先清除旧路线再绘制新路线。

## 7. 常见问题

### 7.1 后端显示 `No module named 'app'`

通常是因为在项目根目录运行了：

```powershell
python -m uvicorn app.main:app --reload
```

请切换到 `backend` 目录后再运行：

```powershell
cd E:\大三下\WebGIS\智游图策\Travel-Agent\backend
python -m uvicorn app.main:app --reload
```

### 7.2 前端没有 POI

优先检查：

- 后端是否启动。
- `/api/pois` 是否 200。
- 数据库是否已有 `scenic_spot`、`hotel`、`metro_station` 数据。
- 前端 `.env` 中 `VITE_API_BASE_URL` 是否正确。

### 7.3 天地图不能显示

优先检查：

- 前端 `.env` 中 `VITE_TIANDITU_KEY` 是否配置。
- Key 类型是否支持浏览器端调用。
- 浏览器 F12 Network 是否出现 403。

如果没有天地图 Key，项目应能降级到 OSM 底图。

### 7.4 高德脚本提示 Key 未配置

检查后端 `.env`：

```env
AMAP_WEB_SERVICE_KEY=
```

并确认是在 `backend` 目录下执行脚本。

### 7.5 数据库连接失败

检查后端 `.env`：

```env
DATABASE_URL=
```

可用下面命令快速验证：

```powershell
python -c "from app.core.config import settings; from sqlalchemy import create_engine, text; e=create_engine(settings.database_url); print(e.connect().execute(text('select 1')).scalar())"
```

正常输出：

```text
1
```

### 7.6 npm 提示磁盘空间不足

如果出现：

```text
ENOSPC: no space left on device
```

需要清理系统磁盘空间或 npm 缓存后重试：

```powershell
npm cache clean --force
```

也可以删除本地构建产物后重新构建：

```powershell
Remove-Item -Recurse -Force dist
npm run build
```

