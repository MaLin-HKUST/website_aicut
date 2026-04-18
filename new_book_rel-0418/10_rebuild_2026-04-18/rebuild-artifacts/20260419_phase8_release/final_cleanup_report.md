# 最终清理报告

时间：2026-04-19

## 已移除的旧运行面

以下旧容器已从 A 机器移除：

- `release0415_worker`
- `release0415_api`
- `release0415_scheduler`
- `pg-f10`

这些对象原本属于旧 `release_0415_slot` / 旧调度链路，已经不再承担正式职责。

## 已停用的旧监听

以下旧前端监听已停止：

- `127.0.0.1:3000`
- `192.168.92.197:3001`

当前正式前端只保留：

- `127.0.0.1:3301`

## 当前保留的正式运行面

### A 机器

- `website_aicut_api_1`
- `a-machine-phase5-postgres`
- `a-machine-phase5-api`
- `a-machine-phase5-scheduler`
- host web on `127.0.0.1:3301`

### Worker 机器

- `worker1-phase6-gateway`

## 当前保留的端口

- `127.0.0.1:8000`
- `127.0.0.1:3301`
- `0.0.0.0:18001`
- `0.0.0.0:55433`

## 尚未删除但仍存在的历史文件

本轮完成的是“运行面收口”，不是“所有历史目录完全清空”。

仍可能存在但未再参与正式流量的历史目录包括：

- `/home/malin/release_0415_slot`
- `/home/malin/website_aicut`
- 旧阶段脚本与历史构建残留

这些目录当前不再承担正式职责，但因为属于文件级清理，不在本轮最小运行面切换中继续扩大破坏面。

## 结论

到本报告为止，A 机器已经从“旧主站线 + slot 前端线 + 旧调度线 + 过渡 Worker 线并存”收敛成：

- 一套正式网站入口
- 一套正式 legacy API / SQLite
- 一套正式 candidate 调度中心
- 一台 Worker 执行节点
