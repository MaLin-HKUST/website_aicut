# 2026-04-18 Phase 3 Service Ownership Matrix

## 1. 目标服务归属表

| 服务/资产 | 长期归属 | 当前状态 | 阶段 3 判定 | 说明 |
| --- | --- | --- | --- | --- |
| `nginx` | A 机器 | 已在 A 机器 | 正式保留 | A 机器唯一公网入口 |
| 正式前端 | A 机器 | 当前走 `3001` | 正式保留 | 最终只能保留一套 |
| 旧前端 `3000` | 无长期归属 | 当前仍存在 | 过渡保留 | 切流稳定后删除 |
| 网站业务 API | A 机器 | 旧 SQLite/API 线存在 | 正式保留 | 继续服务网站主链路 |
| `website_aicut.db` | A 机器 | 仍在旧主站目录 | 正式保留 | 只服务 admin/auth/网站数据 |
| 调度 API | A 机器 | `release0415_api` | 正式保留 | 属于调度中心 |
| Scheduler Runtime | A 机器 | `release0415_scheduler` | 正式保留 | 属于调度中心 |
| PostgreSQL | A 机器 | `pg-f10` | 正式保留 | 当前数据可清空重建 |
| Worker Gateway | Worker 机器 | 当前 A 机器存在过渡版 | 必须迁出 | A 机器仅过渡保留 |
| Smart Cut Worker | Worker 机器 | 当前未正式在 Worker 接管 | 必须迁出 | 不应留在 A 机器 |
| TOS 工具链 | A 机器 + Worker | 当前 A 机器临时在 `/tmp` | 正式保留并转正 | 不应继续停留在 `/tmp` |
| `release_0415_slot` | 无长期归属 | 当前正式流量路径 | 过渡保留 | 新运行面稳定后退出 |
| `website_aicut_git` | A 机器 | 当前已存在 | 正式保留 | 作为远端代码 checkout |
| `website_aicut_repo.git` | A 机器 | 当前已存在 | 正式保留 | 作为远端 bare repo |

## 2. 删除分类

### 立即不能删

- `website_aicut.db`
- `pg-f10` 与阶段 2 备份锚点
- 当前 nginx 配置和证书
- `release_0415_slot`
- `/tmp/tos_uploader_runtime`

### 待新链路稳定后删除

- 旧 `3000` 前端线
- A 机器上的 `release0415_worker`
- `release_0415_slot` 历史 rerun 和验收目录
- `website_aicut_f10_run` 等过渡验证目录
- Created 状态测试容器
- 无主 `<none>` 镜像
- 失败的 scp 中间目录

### 长期必须存在

- A 机器正式前端
- A 机器网站 API
- SQLite
- 调度 API
- Scheduler Runtime
- PostgreSQL
- Worker Gateway
- Smart Cut Worker
- TOS 工具链正式目录
- Git bare repo 与远端 checkout

## 3. TOS 工具链转正规则

当前临时路径：

- `/tmp/tos_uploader_runtime`

正式目标路径：

- `/home/malin/website_aicut_tools/tos_uploader/`

转正完成标准：

- A 机器上有固定目录
- 具备上传和下载能力
- 配置不再依赖 `/tmp`
- 后续数据库备份、release bundle 上传、镜像归档上传都复用这套工具链

## 4. 阶段 3 直接结论

- A 机器不是执行机，只保留网站与调度两层。
- Worker 机器承担 Gateway 与算法执行两层。
- `/tmp/tos_uploader_runtime` 当前不是垃圾文件，而是待转正的正式工具前身。
- 备份真相以 TOS 为主；A 机器只保留执行时短期工作副本。
