# 阶段 8：回滚与恢复演练报告

时间：2026-04-19

## 结论

阶段 8 已完成两类演练：

1. 正式域名入口回滚演练
2. PostgreSQL 备份恢复演练

这意味着当前重建后的系统已经不再是“只能靠记忆修回来的现场状态”，而具备最小可回滚、可恢复能力。

## 演练 1：正式域名入口回滚

### 目的

验证正式域名入口从 candidate `3301` 切回旧 `3001` 再切回 `3301` 的流程是否可执行。

### 操作

对 `/etc/nginx/sites-enabled/xiaomajianji.cn` 做了两次切换：

- `127.0.0.1:3301 -> 192.168.92.197:3001`
- `192.168.92.197:3001 -> 127.0.0.1:3301`

每次切换都执行：

- `nginx -t`
- `systemctl reload nginx`

### 结果

- nginx 配置检查通过
- reload 成功
- 最终公网入口已切回：
  - `127.0.0.1:3301`

### 验证

当前正式域名再次命中 candidate 页面标记：

- `/login`：
  - `小马AI剪辑`
  - `营销视频剪辑智能体`
  - `登录`
- `/welcome`：
  - `小马 AI 剪辑`
  - `小马AI准备就绪`
  - `请点击左侧`

## 演练 2：PostgreSQL 备份恢复

### 目的

验证阶段 2 生成的 PostgreSQL 备份锚点可以在隔离环境中恢复。

### 使用的备份

备份根：

- `/home/malin/website_aicut_backups/pre_rebuild_20260418_224329/postgres/scheduler.sql.gz`

### 隔离恢复环境

临时容器：

- `a-machine-phase8-restore-postgres`

恢复方式：

- 在 A 机器上拉起新的 `postgres:16-alpine`
- 通过 `gunzip -c ... | docker exec -i ... psql ...` 导入 dump

### 恢复结果

恢复后的隔离库已成功出现这些表：

- `scheduler_tasks`
- `smart_cut_devices`
- `smart_cut_edits`
- `smart_cut_tasks`

恢复后查询到的记录数：

- `scheduler_tasks = 59`
- `smart_cut_tasks = 57`
- `smart_cut_devices = 10`

说明备份文件不是空壳，而是有效的可恢复 dump。

### 清理

验证完成后，临时容器和隔离数据目录已移除：

- `a-machine-phase8-restore-postgres`
- `/home/malin/website_aicut_prod/postgres-restore-data`

## 风险说明

- 这次验证的是 PostgreSQL 恢复，没有额外再跑 SQLite 恢复演练。
- 公网入口回滚演练验证的是 nginx 路由级切换，不是重新拉起旧整套运行面。
- 当前线上 candidate API 仍包含热补文件，下一轮正式发布应把这些热补收进标准镜像或标准部署脚本。

## 对下一步的直接指令

阶段 8 已完成，当前系统可以进入“清理历史运行面并保留最终运行面”的收口状态。
