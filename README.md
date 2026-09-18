# 城市绿地养护记录系统

面向城市绿化养护单位的一体化记录系统：以**绿地台账**为主线，串联**养护任务登记**、**养护记录录入**、**绿植更换记录**与**灌溉用水计量**，并提供养护总览看板。

- 后端：Flask 3 + SQLAlchemy 2 + Flask-Migrate + Gunicorn（分层：api / schemas / services / models）
- 前端：Vue 3 + Vite + Vue Router + Pinia + Element Plus + ECharts（按业务模块拆分视图）
- 数据库：本地默认 SQLite，容器编排使用 PostgreSQL 16
- 部署：docker-compose 一键拉起 db / backend / frontend（nginx 托管静态资源并反向代理 /api）

## 一、功能模块

| 模块 | 页面 | 主要能力 |
| --- | --- | --- |
| 养护总览 | `/dashboard` | 绿地与养护总量指标、近半年记录与工时趋势、绿地类型/任务类型/更换原因分布、逾期任务提醒、养护工作量排名 |
| 绿地台账 | `/green-spaces` | 绿地建档（编号自动生成）、按行政区/类型/等级/状态/关键字检索、档案详情（概览 + 近期任务/记录/更换 + 更换原因汇总）、删除保护 |
| 养护任务 | `/tasks` | 任务登记（编号按日生成）、按状态/类型/优先级/绿地/计划日期区间/逾期筛选、状态流转（待执行→进行中→已完成/已取消）、任务详情与执行进度 |
| 养护记录 | `/records` | 记录录入（可关联任务，也可登记日常巡查）、工时/天气/材料/质量评定、质量分布与工时汇总、记录详情 |
| 绿植更换 | `/replacements` | 更换登记（植株、类别、规格、数量、原因、原植株状况、供苗单位、单价与金额）、按类别/原因统计与占比、按绿地/日期区间筛选 |
| 灌溉水源点 | `/water-sources` | 水源点建档（编号自动生成）、水源类型（市政/再生水/河道/自备井/蓄水池等）、所属行政区与取水位置、在用/备用/停用状态、关联绿地、取用次数统计 |
| 灌溉用水 | `/irrigation` | 每次灌溉登记用水量或时长（至少一项）、覆盖绿地与面积、水源点、灌溉方式、执行班组；按行政区×月份汇总用水量，异常偏高的单次用水自动标记；支持仅看异常、按绿地/行政区/方式/日期筛选 |

## 二、目录结构

```
.
├── backend/                     # Flask 后端
│   ├── app/
│   │   ├── __init__.py          # 应用工厂：装配扩展、蓝图、错误处理、CLI
│   │   ├── config.py            # 配置（SQLite / PostgreSQL 切换）
│   │   ├── constants.py         # 业务字典（唯一枚举来源，下发给前端）
│   │   ├── errors.py            # 业务异常与全局错误响应
│   │   ├── cli.py               # init-db / reset-db / seed 命令
│   │   ├── api/                 # 接口层：每个业务模块一个 Blueprint
│   │   │   ├── green_spaces.py
│   │   │   ├── maintenance_tasks.py
│   │   │   ├── maintenance_records.py
│   │   │   ├── plant_replacements.py
│   │   │   ├── water_sources.py
│   │   │   ├── irrigation_records.py
│   │   │   ├── statistics.py
│   │   │   └── meta.py
│   │   ├── schemas/             # 校验层：写库字段校验 + 查询条件解析
│   │   │   ├── common.py        # 链式字段校验器
│   │   │   ├── filters.py       # 列表过滤条件
│   │   │   └── green_space.py / maintenance_task.py / maintenance_record.py / plant_replacement.py / water_source.py / irrigation_record.py
│   │   ├── services/            # 业务层：事务、编号生成、跨模块规则
│   │   │   ├── base_service.py  # 通用增删改与编号冲突重试
│   │   │   ├── code_generator.py
│   │   │   ├── green_space_service.py
│   │   │   ├── maintenance_task_service.py
│   │   │   ├── maintenance_record_service.py
│   │   │   ├── plant_replacement_service.py
│   │   │   ├── water_source_service.py
│   │   │   ├── irrigation_record_service.py
│   │   │   └── statistics_service.py
│   │   ├── models/              # 模型层：SQLAlchemy 模型与序列化
│   │   └── utils/               # 响应封装、分页、日期、排序等
│   ├── tests/                   # pytest 测试（接口 + 业务规则 + 端到端流程）
│   ├── docker/entrypoint.sh     # 等库就绪 → 建表 → 可选写入演示数据
│   ├── requirements.txt
│   └── wsgi.py                  # 入口（flask run / gunicorn 共用）
│
├── frontend/                    # Vue 3 前端
│   ├── src/
│   │   ├── api/                 # 按模块拆分的接口封装 + axios 拦截器
│   │   ├── components/common/   # PageHeader、StatCard、EnumTag、绿地/任务/记录选择器、图表容器
│   │   ├── composables/         # useListQuery（列表分页筛选）、useEnumOptions
│   │   ├── layouts/             # DefaultLayout（侧边导航 + 顶栏）
│   │   ├── router/              # 路由（按模块懒加载）
│   │   ├── stores/              # Pinia：字典缓存、布局状态
│   │   ├── styles/              # 全局样式与主题变量
│   │   ├── utils/               # 数值/面积/金额/日期格式化
│   │   └── views/               # 视图：dashboard / green-space / task / record / replacement / water-source / irrigation
│   ├── docker/nginx.conf        # 静态资源 + /api 反向代理
│   ├── vite.config.js           # 开发代理 /api → 后端
│   └── package.json
│
├── docker-compose.yml           # db + backend + frontend 编排
├── .env.example
└── README.md
```

## 三、快速开始

### 方式一：docker-compose（推荐）

```bash
cp .env.example .env          # 可选：调整端口、数据库口令、是否写入演示数据
docker compose up -d --build
```

启动后访问：

- 前端：<http://localhost:8090>
- 后端接口：<http://localhost:5000/api/v1/meta/health>
- PostgreSQL：`localhost:5432`（容器内 `db:5432`）

首次启动会自动建表；`SEED_DEMO_DATA=true` 时会写入一批演示数据（7 处绿地、17 条任务、23 条养护记录、6 条更换记录、6 个水源点、33 条灌溉用水记录，含 1 条异常偏高样本）。停止与清理：

```bash
docker compose down            # 停止容器，保留数据库卷
docker compose down -v         # 连同数据库卷一起清理
```

### 方式二：本地开发

后端（Python 3.11+，默认使用 SQLite，数据库文件位于 `backend/instance/green_space.db`）：

```bash
cd backend
pip install -r requirements.txt
flask --app wsgi seed --reset      # 建表 + 写入演示数据（可省略）
flask --app wsgi run --debug       # http://127.0.0.1:5000
```

前端（Node 18+）：

```bash
cd frontend
npm install
npm run dev                        # http://127.0.0.1:5173，/api 自动代理到 5000
```

生产构建与本地预览：

```bash
cd frontend && npm run build && npm run preview
```

## 四、环境变量

| 变量 | 作用 | 默认值 |
| --- | --- | --- |
| `DATABASE_URL` | 数据库连接串，留空则使用 SQLite | 空（SQLite） |
| `AUTO_CREATE_TABLES` | 启动时自动建表 | `true` |
| `SEED_DEMO_DATA` | 容器启动时写入演示数据 | `false`（compose 中为 `true`） |
| `CORS_ORIGINS` | 允许的跨域来源 | `*` |
| `DEFAULT_PAGE_SIZE` / `MAX_PAGE_SIZE` | 分页默认与上限 | `10` / `100` |
| `INSTANCE_DIR` | SQLite 数据文件目录 | `backend/instance` |
| `VITE_API_BASE_URL` | 前端接口前缀 | `/api/v1` |
| `VITE_PROXY_TARGET` | 开发代理目标 | `http://127.0.0.1:5000` |

## 五、接口一览（前缀 `/api/v1`）

统一响应结构：成功 `{"success": true, "code": 0, "message": "ok", "data": ...}`；失败 `{"success": false, "code": 4xxxx, "message": "...", "data": {"字段": "提示"}}`。

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/meta/enums` | 全部业务字典（前端下拉唯一来源） |
| GET | `/meta/health` | 健康检查（含数据库连通性） |
| GET | `/green-spaces` | 台账列表（`keyword`/`district`/`green_type`/`maintenance_grade`/`status`/`sort`/`order`/分页，返回汇总） |
| GET | `/green-spaces/options` | 绿地下拉选项（排除已归档） |
| GET | `/green-spaces/districts` | 行政区及绿地处数 |
| POST | `/green-spaces` | 新增绿地（编号可留空自动生成） |
| GET | `/green-spaces/{id}` | 绿地详情 |
| GET | `/green-spaces/{id}/profile` | 绿地档案（概览统计 + 近期任务/记录/更换） |
| PUT | `/green-spaces/{id}` | 更新绿地（编号不可改） |
| DELETE | `/green-spaces/{id}?force=true` | 删除绿地（有关联数据时需 `force`） |
| GET/POST | `/maintenance-tasks` | 任务列表 / 登记任务（`status`/`task_type`/`priority`/`green_space_id`/`date_from`/`date_to`/`overdue`） |
| GET/PUT/DELETE | `/maintenance-tasks/{id}` | 任务详情（含执行进度与记录） / 更新 / 删除（有记录时需 `force`，记录会保留但解除关联） |
| PATCH | `/maintenance-tasks/{id}/status` | 任务状态流转 |
| GET/POST | `/maintenance-records` | 记录列表（`task_id`/`green_space_id`/`quality_result`/`weather`/`unlinked`/日期区间，返回汇总） / 录入记录 |
| GET/PUT/DELETE | `/maintenance-records/{id}` | 记录详情（含关联更换记录） / 更新 / 删除 |
| GET | `/maintenance-records/summary` | 记录汇总（条数、工时、质量分布） |
| GET/POST | `/plant-replacements` | 更换记录列表（`green_space_id`/`plant_category`/`reason`/日期区间，返回汇总） / 登记更换 |
| GET/PUT/DELETE | `/plant-replacements/{id}` | 详情 / 更新 / 删除 |
| GET | `/plant-replacements/summary` | 更换汇总（按植物类别、更换原因） |
| GET/POST | `/water-sources` | 水源点列表（`district`/`source_type`/`status`/`green_space_id`/关键字，返回状态汇总与取用次数） / 建档 |
| GET | `/water-sources/options` | 水源点下拉（可按 `district`/`green_space_id` 过滤，停用水源点不返回） |
| GET/PUT/DELETE | `/water-sources/{id}` | 详情 / 更新 / 删除（已有灌溉记录的水源点禁止删除，返回 409） |
| GET/POST | `/irrigation-records` | 灌溉记录列表（`green_space_id`/`water_source_id`/`district`/`method`/日期区间/`abnormal_only`，返回汇总，行内带 `is_abnormal`） / 登记灌溉用水 |
| GET/PUT/DELETE | `/irrigation-records/{id}` | 详情 / 更新 / 删除 |
| GET | `/irrigation-records/summary` | 用水量汇总：行政区×月份合计、异常次数与异常偏高明细 |
| GET | `/statistics/dashboard` | 看板聚合数据（总览 + 分布 + 趋势 + 榜单 + 提醒 + 最近动态） |
| GET | `/statistics/overview` `/distributions` `/trends` `/ranking` `/reminders` | 看板分项接口 |

## 六、业务规则

1. **业务编号**：绿地 `GS-年份-序号`（如 `GS-2026-0001`），任务 `MT-YYYYMMDD-序号`，养护记录 `MR-YYYYMMDD-序号`，更换记录 `PR-YYYYMMDD-序号`；留空自动生成，唯一约束冲突时自动重试，编号创建后不可修改。
2. **任务状态联动**（`maintenance_record_service`）：
   - 任务下有养护记录后，任务自动从「待执行」进入「进行中」；
   - 存在**合格**记录且**没有不合格**记录时，任务自动置为「已完成」并写入完成时间；
   - 存在不合格记录时任务保持「进行中」，必须整改复检（把记录改判为合格或删除）后才会完成，手动「标记完成」同样会被拒绝；
   - 删除养护记录后按剩余记录重新推算任务状态，避免出现「已完成却没有记录」；已取消的任务不允许补录记录。
3. **绿地归属一致性**：养护记录可只填绿地（日常养护）或只填任务（绿地自动跟随任务）；两者同时提供时必须属于同一绿地。更换记录若关联养护记录，必须是同一绿地的记录。
4. **日期约束**：养护日期、更换日期不得早于绿地建成日期。
5. **金额核算**：更换金额 = 数量 × 单价，由后端统一计算；未填单价时金额留空，前端提示补录。
6. **删除保护**：删除绿地时若已存在任务/记录/更换/灌溉数据会返回 409 并给出数量明细，需 `force=true` 才级联删除（该绿地下的水源点解除关联保留）；删除任务时养护记录默认保留（解除关联），避免养护履历丢失。
7. **字典单一来源**：所有枚举在 `backend/app/constants.py` 定义，前端通过 `/meta/enums` 获取并缓存，前后端不重复维护。
8. **灌溉用水计量**：
   - 水源点编号 `WS-年份-序号`，灌溉记录编号 `IR-YYYYMMDD-序号`，留空自动生成且创建后不可修改；
   - 每次灌溉的**用水量（吨）与灌溉时长（分钟）至少登记一项**；覆盖面积不得大于绿地总面积，关联养护记录必须与覆盖绿地一致；
   - 用水量按「**行政区 × 自然月**」汇总（次数、用水量、时长、异常次数）；
   - **异常偏高判定**：同一行政区同一月份样本不少于 3 次时，用稳健的 MAD 修正标准分 `M = 0.6745×(x−中位数)/MAD`，`M ≥ 3.5` 标记为异常偏高（MAD 为 0 时退化为超过中位数 3 倍）；判定基于全量记录，不受查询筛选影响；
   - 已有灌溉记录引用的水源点不可删除（返回 409），可改为「停用」，停用后不再出现在登记下拉中但用水台账保留取水溯源。

## 七、数据模型

| 表 | 说明 | 关键字段 |
| --- | --- | --- |
| `green_space` | 绿地台账 | `code`(唯一)、`name`、`district`、`green_type`、`maintenance_grade`、`area_sqm`、`status`、`manager`、`established_date` |
| `maintenance_task` | 养护任务 | `task_no`(唯一)、`green_space_id`、`task_type`、`plan_date`、`priority`、`executor`、`status`、`completed_at` |
| `maintenance_record` | 养护记录 | `record_no`(唯一)、`task_id`(可空)、`green_space_id`、`record_date`、`work_content`、`worker`、`work_hours`、`weather`、`quality_result` |
| `plant_replacement` | 绿植更换记录 | `replacement_no`(唯一)、`green_space_id`、`maintenance_record_id`(可空)、`plant_name`、`plant_category`、`quantity`、`unit`、`reason`、`unit_price`、`amount` |
| `water_source` | 灌溉水源点 | `source_no`(唯一)、`name`、`source_type`、`district`、`address`、`green_space_id`(可空)、`status`、`manager`、`installed_date` |
| `irrigation_record` | 灌溉用水记录 | `record_no`(唯一)、`green_space_id`、`water_source_id`、`maintenance_record_id`(可空)、`irrigation_date`、`method`、`water_volume`(可空)、`duration_minutes`(可空)、`covered_area_sqm`、`worker_team` |

绿地删除时任务/记录/更换/灌溉级联清理，水源点解除关联（外键 `SET NULL`）保留；任务与养护记录之间、养护记录与更换/灌溉记录之间为可空外键（`SET NULL`），保证养护履历可独立留存。

## 八、测试

```bash
cd backend
python -m pytest              # 76 个用例：接口、校验、跨模块规则、端到端流程
```

覆盖重点：绿地编号生成与唯一性、枚举与字段校验、列表过滤/排序/分页、任务状态自动流转与手动流转限制、记录删除后的状态回退、更换金额核算、水源点建档/停用与删除保护、灌溉用水量或时长至少一项、覆盖面积上限、行政区×月份汇总口径、异常偏高（MAD 修正标准分）标记与筛选、删除保护与强制删除、统计聚合口径一致性、演示数据自洽性。

## 九、常见问题

- **前端页面正常但数据为空**：确认后端已启动且 `/api/v1/meta/health` 返回 `database: up`；容器方式下检查 `docker compose ps` 中 backend 是否 `healthy`。
- **端口被占用**：修改 `.env` 中的 `FRONTEND_PORT` / `BACKEND_PORT`，或在本地开发时用 `flask --app wsgi run --port 5001` 并同步调整 `VITE_PROXY_TARGET`。
- **数据库结构变更**：切换 `AUTO_CREATE_TABLES=false` 后使用 Flask-Migrate：`flask --app wsgi db init && flask --app wsgi db migrate -m "描述" && flask --app wsgi db upgrade`。
- **重置演示数据**：`flask --app wsgi seed --reset`；容器方式可执行 `docker compose exec backend flask --app wsgi seed --reset`。
