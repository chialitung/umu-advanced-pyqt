# UMU LMS 客户端 SDK（含 PyQt6 图形界面）

本项目是一套针对 UMU 学习管理系统（`www.umu.cn`）的 Python SDK，通过 HAR 文件逆向工程方式解析其 HTTP API 协议，封装为可直接调用的 Python API。同时提供 PyQt6 构建的桌面图形界面和命令行工具（CLI），兼顾开发者集成和终端用户直接使用两种场景。

---

## 一、技术栈概览

| 层级 | 技术选型 | 版本要求 | 用途说明 |
|------|----------|----------|----------|
| 编程语言 | Python | >= 3.10 | 支持 `str \| None` 联合类型语法，`from __future__ import annotations` 类型提示 |
| HTTP 通信 | requests | >= 2.31.0 | Session 连接池、Cookie 自动管理、请求重试与指数退避 |
| 数据验证 | pydantic | >= 2.5.0 | 请求/响应数据结构校验与序列化 |
| ORM / 数据库 | SQLAlchemy | >= 2.0.0 | 跨 SQLite / PostgreSQL 的统一 ORM，支持自动建表与批量 merge 写入 |
| 数据处理 | pandas + openpyxl | >= 2.1.0 / >= 3.1.0 | DataFrame 查询、CSV / Excel(xlsx) 导出 |
| 配置解析 | pyyaml + python-dotenv | >= 6.0.1 / >= 1.0.0 | YAML 配置与环境变量管理 |
| 安全加密 | cryptography | >= 42.0.0 | Token 加密存储与敏感信息保护 |
| 桌面 GUI | PyQt6 + qtawesome | >= 6.6.0 / >= 1.3.0 | 跨平台原生桌面界面，含图标字体与自定义组件库 |
| 测试框架 | pytest + responses | >= 7.4.0 / >= 0.24.0 | HTTP Mock 测试与覆盖率统计 |

---

## 二、分层架构

项目采用自上而下的四层架构，数据流单向传递，各层职责清晰解耦：

```
GUI 桌面应用 (src/gui/)
    ↓ 调用
Endpoint 业务层 (src/lms_client/endpoints/)
    ↓ 调用
HTTP 客户端层 (src/lms_client/client.py)
    ↓ 委托
认证层 (src/lms_client/auth.py)
    ↓ HTTP 请求
UMU 官方 API
    ↓ 返回数据
存储/导出层 (src/lms_client/storage/)
```

### 1. 认证层（Auth）

`src/lms_client/auth.py` 提供可插拔的认证策略，支持三种模式：

- **SessionAuth**（默认）：基于 `requests.Session` 的 Cookie 会话认证，完整复现浏览器 HAR 流量中的登录态。`LMSClient.request()` 对此做特殊处理，直接调用 `auth.session.request()`，确保 Cookie 由同一个 Session 对象自动维护。
- **TokenAuth**：Bearer Token 方式，支持通过 `refresh_token` 或用户名/密码重新登录实现自动续期。
- **AuthFactory**：根据 HAR 分析元数据自动选择最优认证策略。

### 2. HTTP 客户端层（LMSClient）

`src/lms_client/client.py` 是核心 HTTP 客户端，封装了与 UMU API 交互的全部网络细节：

- **连接管理**：内部使用 `requests.Session`，自动实现连接复用。
- **重试机制**：遇到 `LMSAuthError`、`LMSRateLimitError`（429）或 `requests.RequestException` 时自动重试，支持指数退避；认证失败时先尝试刷新再重试。
- **路径参数**：支持 REST 风格的路径模板替换（如 `/uapi/v1/users/{user_id}`）。
- **分页遍历**：`list_all()` 方法自动处理分页参数，逐页请求并合并结果。
- **批量并发**：`batch_get()` / `batch_create()` 提供并发请求能力，提升大数据量操作效率。
- **错误映射**：状态码映射到具体异常类（400/422 → `LMSValidationError`、401/403 → `LMSAuthError`、404 → `LMSNotFoundError`、429 → `LMSRateLimitError`），方便调用方精确捕获。

### 3. 业务 Endpoint 层

`src/lms_client/endpoints/` 按业务域拆分为独立模块：

| 模块 | 覆盖范围 | 典型方法 |
|------|----------|----------|
| `users.py` | 用户管理 | `list_enterprise_users`, `batch_add_user_to_group` |
| `organizations.py` | 组织架构 | `get_info`, `list_departments_by_level` |
| `courses.py` | 课程管理 | 课程列表、详情查询 |
| `exams.py` | 考试模块 | 考试列表、成绩查询 |
| `reports.py` | 报表统计 | `list_report_groups`, `get_report_group_count` |
| `resources.py` | 资源管理 | 资源上传、下载、列表 |

`base.py` 中的 `EndpointBase` 提供通用 CRUD（`list` / `get` / `create` / `update` / `delete`），但各业务端点优先采用**显式命名方法**（如 `list_departments_by_level`），每个方法对应一条从 HAR 分析中发现的实际 API 路由，避免泛型抽象带来的语义模糊。

### 4. 存储与导出层

`src/lms_client/storage/` 负责数据持久化和多格式导出：

- **DatabaseManager** (`database.py`)：SQLAlchemy ORM 封装，支持 SQLite（本地开发）和 PostgreSQL（生产部署）。`create_tables()` 自动建表，`save()` 通过 `session.merge()` 实现批量 upsert。
- **数据模型** (`models.py`)：声明式 ORM 模型（`User`、`Course`、`Organization` 等），`DatabaseManager.TABLE_MODEL_MAP` 将表名字符串映射到模型类。
- **DataExporter** (`exporter.py`)：基于 pandas 和 openpyxl，支持将查询结果导出为 CSV、Excel(xlsx)、JSON 三种格式。
- **迁移工具**：`migrate_from_api()` 可将 API 端点数据一键拉取并持久化到本地数据库。

### 5. 图形界面层（GUI）

`src/gui/` 是基于 PyQt6 构建的独立桌面应用，为不习惯命令行的终端用户提供可视化操作界面：

- **页面架构**：采用多页面设计（`login_page`、`users_page`、`courses_page`、`governance_page`、`config_page`），通过侧边栏导航切换。
- **组件库**：`components/` 目录包含高度封装的自定义控件——`sidebar`（侧边栏导航）、`styled_button`（统一风格按钮）、`stat_card`（统计卡片）、`progress_bar`（进度条）、`toast`（消息通知）、`step_indicator`（步骤指示器）、`empty_state`（空状态提示）。
- **服务层**：`services/` 目录实现业务逻辑解耦——`auth_service`（认证状态管理）、`config_service`（配置读写与持久化）、`sync_service`（数据同步调度）、`governance_service`（合规检查与治理逻辑）。
- **样式系统**：`styles.py` 集中管理全局配色与控件样式，`icons.py` 基于 qtawesome 提供统一图标资源。
- **日志系统**：`log_config.py` 配置 GUI 运行时的日志输出，便于排查问题。

---

## 三、HAR 逆向分析流水线

`scripts/` 目录包含一套单向流水线工具，用于将浏览器捕获的 HAR 流量转换为可维护的 OpenAPI 规范：

```
HAR 原始文件 → inspect_har.py → har_analyzer.py → parameter_inferencer.py → generate_openapi.py → docs/openapi.yaml
```

1. **inspect_har.py**：验证 HAR 文件格式并生成摘要统计。
2. **har_analyzer.py**：提取其中的 HTTP 请求，解析 URL、方法、参数、响应结构。
3. **parameter_inferencer.py**：通过语义推断为参数补充业务含义（如 `page` → 分页页码、`size` → 每页条数）。
4. **generate_openapi.py**：输出标准 OpenAPI 3.0 规范的 `openapi.yaml`。

该流水线实现了"捕获即文档化"——每次重新抓取 HAR 并运行流水线，即可同步更新 API 规范。

---

## 四、项目目录结构

```
release/
├── Launch.py                      # GUI 程序入口（可直接双击运行）
├── pyproject.toml                 # 项目元数据与依赖声明
├── requirements.txt               # 精简版依赖列表
├── README.md                      # 本文件
├── src/
│   ├── lms_client/                # SDK 核心包
│   │   ├── __init__.py
│   │   ├── auth.py                # 认证策略（SessionAuth / TokenAuth / AuthFactory）
│   │   ├── client.py              # LMSClient HTTP 客户端
│   │   ├── exceptions.py          # 异常层级（LMSAPIError → 各子类）
│   │   ├── cli.py                 # 命令行工具实现
│   │   ├── timeutil.py            # 时间工具函数
│   │   ├── endpoints/             # 业务端点
│   │   │   ├── base.py            # EndpointBase 通用 CRUD
│   │   │   ├── users.py           # 用户端点
│   │   │   ├── organizations.py   # 组织架构端点
│   │   │   ├── courses.py         # 课程端点
│   │   │   ├── exams.py           # 考试端点
│   │   │   ├── reports.py         # 报表端点
│   │   │   └── resources.py       # 资源端点
│   │   └── storage/               # 数据持久化与导出
│   │       ├── __init__.py
│   │       ├── database.py        # DatabaseManager（SQLAlchemy 封装）
│   │       ├── models.py          # ORM 数据模型
│   │       └── exporter.py        # DataExporter（CSV/Excel/JSON）
│   └── gui/                       # PyQt6 桌面图形界面
│       ├── __init__.py
│       ├── main.py                # GUI 入口（对应 lms-gui 命令）
│       ├── main_window.py         # 主窗口框架
│       ├── styles.py              # 全局样式表
│       ├── icons.py               # 图标资源（qtawesome）
│       ├── log_config.py          # 日志配置
│       ├── components/            # 可复用 UI 组件
│       │   ├── sidebar.py
│       │   ├── styled_button.py
│       │   ├── stat_card.py
│       │   ├── progress_bar.py
│       │   ├── toast.py
│       │   ├── step_indicator.py
│       │   ├── empty_state.py
│       │   └── governance_result_window.py
│       ├── pages/                 # 业务页面
│       │   ├── login_page.py
│       │   ├── users_page.py
│       │   ├── courses_page.py
│       │   ├── governance_page.py
│       │   └── config_page.py
│       └── services/              # GUI 业务服务层
│           ├── auth_service.py
│           ├── config_service.py
│           ├── sync_service.py
│           └── governance_service.py
└── tests/                         # 测试用例（pytest + responses 模拟 HTTP）
```

---

## 五、安装与运行

### 5.1 基础安装

```bash
pip install -e .
```

安装后系统会注册两个命令行入口：
- `lms-cli` — 命令行工具
- `lms-gui` — 启动图形界面

### 5.2 开发依赖（含测试框架）

```bash
pip install -e ".[dev]"
```

### 5.3 运行图形界面

```bash
# 方式一：命令行启动
lms-gui

# 方式二：直接运行入口文件
python Launch.py
```

---

## 六、快速上手

### 6.1 SDK 直接调用

```python
from lms_client import LMSClient, SessionAuth

auth = SessionAuth()
client = LMSClient(base_url="https://www.umu.cn", auth=auth)

# 获取企业信息
info = client.get("/uapi/v1/enterprise/info")
print(info)

# 分页自动遍历所有用户
all_users = client.list_all("/uapi/v1/enterprise/user-list", data_key="data")
```

### 6.2 使用业务端点模块

```python
from lms_client import LMSClient, SessionAuth
from lms_client.endpoints import OrganizationEndpoint, UserEndpoint, ReportEndpoint

client = LMSClient(auth=SessionAuth())
org = OrganizationEndpoint(client)
users = UserEndpoint(client)
reports = ReportEndpoint(client)

# 组织架构信息
print(org.get_info())

# 企业用户列表
print(users.list_enterprise_users())

# 报表分组（分页）
result = reports.list_report_groups(page=1, size=20)
print(result["data"]["page_info"])

# 快速获取总数（不拉取全量数据）
print(reports.get_report_group_count())
```

### 6.3 数据持久化与导出

```python
from lms_client.storage import DatabaseManager
from lms_client.storage.exporter import DataExporter

# 初始化 SQLite 数据库
db = DatabaseManager("sqlite:///lms.db")
db.create_tables()

# 批量保存数据
db.save("users", [{"user_id": "123", "name": "张三"}])

# 导出为 Excel
exporter = DataExporter(db)
exporter.export_to_excel("users", "users.xlsx")
```

### 6.4 命令行工具

```bash
# 登录
lms-cli login --url https://www.umu.cn --username YOUR_USER --password YOUR_PASS

# 导出用户列表
lms-cli list-users --output users.xlsx

# 同步 API 数据到本地数据库
lms-cli sync --db sqlite:///lms.db

# 导出所有表
lms-cli export-all --output-dir ./exports --format xlsx
```

---

## 七、异常处理机制

SDK 定义了以 `LMSAPIError` 为根的异常层级：

| 异常类 | 触发条件 | 自动重试 |
|--------|----------|----------|
| `LMSValidationError` | HTTP 400 / 422，请求参数非法 | 否 |
| `LMSAuthError` | HTTP 401 / 403，认证失败 | **是**（先刷新认证） |
| `LMSNotFoundError` | HTTP 404，资源不存在 | 否 |
| `LMSRateLimitError` | HTTP 429，触发限流 | **是**（指数退避） |

调用方可根据具体异常类型做差异化处理，无需手动解析状态码。

---

## 八、安全提示

- HAR 文件可能包含敏感信息（Cookie、Token、密码），务必通过 `.gitignore` 排除 `data/har/*.har` 文件。
- 数据库文件（`*.db`）同样不应提交到版本控制。
- 生产环境请使用环境变量或 `.env` 文件管理凭证，避免硬编码。
- `cryptography` 库用于本地敏感配置的加密存储，密钥请妥善保管。

---

## 九、开发规范

- **Python 版本**：>= 3.10，类型提示使用 `str \| None` 语法和 `from __future__ import annotations`。
- **导入风格**：`src/lms_client/` 内部使用相对导入，测试代码使用绝对导入。
- **测试**：使用 `responses` 库模拟 HTTP 响应，避免对外网产生真实请求。测试夹具集中定义于 `tests/conftest.py`。

---

## License

MIT
