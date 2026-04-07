# Admin 与主站合并迁移计划

## 目标

1. 主数据库从 PostgreSQL 迁移到 SQLite
2. Admin 登录后的管理页面功能完全对标 admindb_test（企业管理、用户管理、素材库、标签管理、自定义标签组）
3. Admin 创建的数据在业务系统中可用（用户能真实登录使用）

## 关键决策

- **主键类型**：保留 API 的 int 自增主键，Admin API 返回时将 int 包装成 `company_id`/`user_id` 等格式适配前端
- **前端技术栈**：用现有 Next.js + Tailwind 重写 admin 页面
- **密码存储**：保持 PBKDF2 hash（不显示明文密码，提供重置功能）

---

## Phase 1: 数据模型扩展（models.py）

### 1.1 扩展现有 Company 表

新增字段（兼容 admindb_test 的 `company` 表）：
- `monthly_video_quota: Mapped[int]` - 月视频额度
- `monthly_video_remaining: Mapped[int]` - 剩余条数
- `billing_cycle_start_date: Mapped[str]` - 计费周期起始 (YYYY-MM-DD)
- `tts_enabled: Mapped[bool]` - TTS开关
- `ai_voice_monthly_usage: Mapped[int]` - AI语音月使用量
- `ai_voice_usage_start_date: Mapped[str | None]` - 语音使用起始日期
- `asset_library_id: Mapped[int | None]` - 关联素材库ID（外键→asset_libraries）
- `status: Mapped[str]` - 状态 (active/inactive)，默认"active"
- `updated_at: Mapped[datetime]` - 更新时间

### 1.2 扩展现有 User 表

新增字段：
- `user_name: Mapped[str | None]` - 用户显示名称
- `status: Mapped[str]` - 状态 (active/inactive)，默认"active"
- `updated_at: Mapped[datetime]` - 更新时间

**说明**：`username` 字段同时作为 Admin 的 `login_account`，`password_hash` 保持 PBKDF2。

### 1.3 新增 Admin 专用表

**AssetLibrary**（素材库）：
- `id: int PK`
- `company_id: int FK → companies.id`（每个企业一个素材库，逻辑一对一）
- `library_name: str`
- `root_path: str`
- `config_path: str`
- `config_version: str | None`
- `config_import_status: str` - pending/success/failed
- `config_import_time: datetime | None`
- `description: str | None`
- `status: str` - active/inactive

**AssetLibraryTagGroup**（标签组）：
- `id: int PK`
- `asset_library_id: int FK`
- `group_key: str`
- `group_name: str`
- `group_order: int` - 排序
- `allow_multi_select: bool`
- `allow_select_all: bool`
- `source_type: str` - config/custom
- `status: str`

**AssetLibraryTag**（标签）：
- `id: int PK`
- `asset_library_id: int FK`
- `tag_group_id: int FK → asset_library_tag_groups`
- `tag_key: str`
- `tag_name: str`
- `filter_condition: str` - 筛选条件（SQL片段或JSON）
- `filter_path: str | None`
- `source_value: str | None`
- `tag_order: int`
- `is_default_selected: bool`
- `status: str`

**UserCustomTagGroup**（用户自定义标签组）：
- `id: int PK`
- `company_id: int FK`
- `user_id: int FK → users.id`
- `asset_library_id: int FK`
- `group_name: str`
- `description: str | None`
- `status: str`

**UserCustomTagGroupItem**（自定义标签组明细）：
- `id: int PK autoincrement`
- `custom_tag_group_id: int FK → user_custom_tag_groups`
- `tag_id: int FK → asset_library_tags`
- `created_at: datetime`

### 1.4 关系定义

- Company ↔ AssetLibrary（一对一逻辑关系，通过 company.asset_library_id）
- AssetLibrary ↔ AssetLibraryTagGroup（一对多）
- AssetLibraryTagGroup ↔ AssetLibraryTag（一对多）
- User ↔ UserCustomTagGroup（一对多）
- UserCustomTagGroup ↔ AssetLibraryTag（多对多，通过 UserCustomTagGroupItem）

---

## Phase 2: Admin API 路由（main.py 中新增）

使用 `/admin/api/` 前缀（区别于现有的 `/admin/` 路由），返回格式适配 admindb_test 前端。

### 2.1 企业管理

```
GET    /admin/api/companies              → 列表
POST   /admin/api/companies              → 创建
GET    /admin/api/companies/{id}         → 详情
PUT    /admin/api/companies/{id}         → 更新（支持动态字段）
DELETE /admin/api/companies/{id}         → 删除
```

返回示例：
```json
{
  "company_id": 1,
  "company_name": "某企业",
  "monthly_video_quota": 100,
  "monthly_video_remaining": 100,
  "billing_cycle_start_date": "2026-04-01",
  "tts_enabled": true,
  "ai_voice_monthly_usage": 0,
  "ai_voice_usage_start_date": null,
  "asset_library_id": null,
  "status": "active",
  "created_at": "2026-04-01T00:00:00",
  "updated_at": "2026-04-01T00:00:00"
}
```

**注意**：返回时将 `id` 映射为 `company_id`，所有字段名保持和 admindb_test 一致。

### 2.2 用户管理

```
GET    /admin/api/users                  → 列表
POST   /admin/api/users                  → 创建
GET    /admin/api/users/{id}             → 详情
PUT    /admin/api/users/{id}             → 更新
DELETE /admin/api/users/{id}             → 删除
```

返回示例：
```json
{
  "user_id": 1,
  "company_id": 1,
  "login_account": "rbzj",
  "user_name": "人博主",
  "status": "active"
}
```

**注意**：
- 返回时用 `login_account` 代替 `username`
- 不返回 `password_hash`，只返回 `user_id` 等必要字段
- 创建用户时后端自动 PBKDF2 hash 密码
- 编辑用户时如果密码字段有值，重新 hash 存储；空值则保持原密码

### 2.3 素材库管理

```
GET    /admin/api/libraries              → 列表
POST   /admin/api/libraries              → 创建
GET    /admin/api/libraries/{id}         → 详情
PUT    /admin/api/libraries/{id}         → 更新
DELETE /admin/api/libraries/{id}         → 删除
POST   /admin/api/libraries/{id}/import  → 模拟导入配置
GET    /admin/api/libraries/{id}/tag-groups → 获取素材库的标签组
GET    /admin/api/libraries/{id}/tags    → 获取素材库的所有标签
```

返回示例：
```json
{
  "asset_library_id": 1,
  "company_id": 1,
  "library_name": "默认素材库",
  "root_path": "/data/library1",
  "config_path": "/data/library1/config.json",
  "config_version": null,
  "config_import_status": "pending",
  "config_import_time": null,
  "description": null,
  "status": "active"
}
```

**注意**：素材库创建后，关联更新 `companies.asset_library_id`。

### 2.4 标签组管理

```
POST   /admin/api/tag-groups             → 创建
PUT    /admin/api/tag-groups/{id}        → 更新
DELETE /admin/api/tag-groups/{id}        → 删除
```

### 2.5 标签管理

```
GET    /admin/api/tag-groups/{id}/tags   → 获取标签组下的标签
POST   /admin/api/tags                   → 创建
PUT    /admin/api/tags/{id}              → 更新
DELETE /admin/api/tags/{id}              → 删除
```

### 2.6 自定义标签组管理

```
GET    /admin/api/custom-groups          → 列表
POST   /admin/api/custom-groups          → 创建（含标签关联）
GET    /admin/api/custom-groups/{id}     → 详情（含 tag_ids）
PUT    /admin/api/custom-groups/{id}     → 更新（更新关联标签）
DELETE /admin/api/custom-groups/{id}     → 删除（级联删除关联项）
GET    /admin/api/users/{id}/custom-groups → 获取用户的自定义标签组
```

---

## Phase 3: Admin 前端重写（web/app/admin/page.tsx）

用 Next.js + Tailwind CSS 重写 admin 页面，功能完全对标 admindb_test。

### 3.1 页面结构

- **顶部导航栏**：5个 Tab 按钮（企业管理、用户管理、素材库、标签管理、自定义标签组）
- **主内容区**：根据选中 Tab 显示数据表格
- **模态框**：新增/编辑数据的弹出表单

### 3.2 各模块功能

| 模块 | 功能 |
|------|------|
| **企业管理** | 表格展示（名称、额度/剩余、TTS、状态）；新增/编辑/删除；模态框含名称、额度、剩余、计费周期、TTS开关、状态 |
| **用户管理** | 表格展示（账号、用户名称、所属企业、状态）；新增/编辑/删除；创建/编辑时有密码输入框；列表不显示密码 |
| **素材库管理** | 表格展示（名称、所属企业、导入状态、状态）；导入配置、编辑、删除；模态框含企业、名称、根路径、配置文件路径、描述 |
| **标签管理** | 左右分栏：左侧标签组列表（点击选中），右侧该组下标签列表；新增标签组/标签；级联下拉（素材库→标签组） |
| **自定义标签组** | 表格展示（组名称、所属用户、标签数、状态）；查看详情（弹窗显示包含的标签）、编辑、删除；级联下拉（企业→用户、素材库→标签列表） |

### 3.3 API 调用路径

通过现有代理转发：
- `/api/proxy/admin/api/companies` → API `localhost:8000/admin/api/companies`
- 以此类推

### 3.4 认证流程

1. 页面加载时调用 `/api/proxy/auth/me` 验证身份
2. 非 admin 角色重定向到 `/welcome`
3. 未登录重定向到 `/login`

---

## Phase 4: 数据库迁移（PostgreSQL → SQLite）

### 4.1 线上数据现状

- PostgreSQL 当前只有 admin 和 rbzj 两个用户
- sessions 表可能有 session 记录
- scheduler_tasks, smart_cut_tasks 等表为空
- 需要保留所有表结构

### 4.2 迁移方案

**步骤1：导出 PostgreSQL 数据**
```bash
pg_dump -U scheduler -d scheduler --data-only --inserts > /tmp/pg_data.sql
```

**步骤2：本地构建新的 SQLite 数据库**
- 使用更新后的 models.py（含扩展字段和新表）
- SQLAlchemy `Base.metadata.create_all()` 自动建表
- 默认新列值为空/默认值

**步骤3：导入数据**
- 将 pg_data.sql 转换为 SQLite INSERT 语句
- 或者直接通过 Python 脚本读取 PostgreSQL 写入 SQLite

**步骤4：更新 admin 用户**
- admin 用户的现有字段保持不变
- 新字段使用默认值

### 4.3 迁移脚本

编写一个一次性 Python 脚本，用于：
1. 连接 PostgreSQL 读取所有数据
2. 连接新的 SQLite 数据库
3. 按表逐个迁移数据
4. 处理字段映射（如 Company 新增字段用默认值）

---

## Phase 5: 部署更新

### 5.1 docker-compose.yml 修改

```yaml
version: "3.3"
services:
  api:
    image: website_aicut-api:sqlite-admin  # 新构建的镜像
    environment:
      DATABASE_URL: sqlite:///data/website_aicut.db
    volumes:
      - ./data:/data  # 挂载 SQLite 数据库文件
    ports:
      - "127.0.0.1:8000:8000"

  web:
    image: website_aicut-web:admin  # 新构建的镜像（含重写后的 admin 页面）
    environment:
      INTERNAL_API_BASE_URL: http://api:8000
    ports:
      - "127.0.0.1:3000:3000"
    depends_on:
      - api

  # db 服务已移除
```

### 5.2 构建步骤

1. 本地修改代码（models.py, main.py, schemas.py, crud.py, admin/page.tsx）
2. 构建新 API 镜像：`docker build -t website_aicut-api:sqlite-admin ./apps/api`
3. 构建新 Web 镜像：`docker build -t website_aicut-web:admin ./apps/web`
4. 保存镜像到 tar 文件：`docker save website_aicut-api:sqlite-admin > api-admin.tar`
5. 上传并加载到服务器
6. 停止现有服务：`docker-compose down`
7. 更新 docker-compose.yml
8. 上传 SQLite 数据库文件到 `./data/`
9. 启动服务：`docker-compose up -d`

### 5.3 Nginx 配置

无需修改。/admin 路由已经指向 web 服务（端口3000），web 的 Next.js 会渲染 admin 页面。

---

## Phase 6: 测试验证

### 6.1 数据迁移验证

- [ ] admin 用户可正常登录
- [ ] rbzj 用户可正常登录
- [ ] 用户角色正确（admin/admin, rbzj/user）

### 6.2 Admin 功能验证

- [ ] 企业管理：增删改查
- [ ] 用户管理：增删改查、密码重置
- [ ] 素材库管理：增删改查、导入配置
- [ ] 标签管理：标签组增删改查、标签增删改查
- [ ] 自定义标签组：增删改查、级联下拉正常

### 6.3 业务系统验证

- [ ] 新创建的用户可以登录业务系统
- [ ] 登录后的 TTS 等功能正常
- [ ] 调度器等功能正常

---

## 执行步骤汇总

| 步骤 | 任务 | 文件 | 工作量 |
|------|------|------|--------|
| 1 | 扩展 models.py | apps/api/app/models.py | 大（新增5个表，扩展2个表） |
| 2 | 扩展 schemas.py | apps/api/app/schemas.py | 中（新增 Admin schema） |
| 3 | 新增 Admin API 路由 | apps/api/app/main.py | 大（约20个新路由） |
| 4 | 扩展 crud.py | apps/api/app/crud.py | 中（新增 CRUD 函数） |
| 5 | 重写 Admin 前端 | apps/web/app/admin/page.tsx | 大（完整管理面板） |
| 6 | 编写数据库迁移脚本 | scripts/migrate_pg_to_sqlite.py | 中 |
| 7 | 更新 docker-compose.yml | docker-compose.yml | 小 |
| 8 | 构建并部署 | - | 中 |
| 9 | 测试验证 | - | 中 |

---

## 风险与注意事项

1. **数据迁移风险**：PostgreSQL JSON 列在 SQLite 中是 TEXT，需要确保序列化/反序列化正常
2. **密码兼容性**：新系统继续用 PBKDF2 hash，Admin 前端不显示明文密码
3. **外键约束**：SQLite 默认外键约束关闭，需要在 SQLAlchemy engine 中启用 `PRAGMA foreign_keys = ON`
4. **并发写**：SQLite 多线程并发写有限制，需要确保数据库文件可写且不被多个进程同时写
5. **回滚准备**：保留 PostgreSQL 备份镜像，万一需要回滚可快速恢复

---

## 附录：字段映射表

### Company ↔ 企业

| admindb_test 字段 | API 字段 | 说明 |
|-------------------|----------|------|
| company_id | id | 返回时映射为 company_id |
| company_name | name | |
| monthly_video_quota | monthly_video_quota | 新增 |
| monthly_video_remaining | monthly_video_remaining | 新增 |
| billing_cycle_start_date | billing_cycle_start_date | 新增 |
| tts_enabled | tts_enabled | 新增 |
| ai_voice_monthly_usage | ai_voice_monthly_usage | 新增 |
| ai_voice_usage_start_date | ai_voice_usage_start_date | 新增 |
| asset_library_id | asset_library_id | 新增（外键） |
| status | status | 新增（默认 active） |
| created_at | created_at | |
| updated_at | updated_at | 新增 |

### User ↔ 用户

| admindb_test 字段 | API 字段 | 说明 |
|-------------------|----------|------|
| user_id | id | 返回时映射为 user_id |
| company_id | company_id | 外键 |
| login_account | username | 返回时映射为 login_account |
| password | password_hash | PBKDF2 hash，不返回 |
| user_name | user_name | 新增 |
| status | status | 新增（默认 active） |
| created_at | created_at | |
| updated_at | updated_at | 新增 |
| role | role | 现有字段 |
