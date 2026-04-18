# 进入阶段 6 前的补充清理报告

时间：2026-04-19

## 目标

在不影响以下对象的前提下，再做一轮补充清理：

- 当前正式公网流量路径
- 阶段 5 候选运行面
- 已形成的回滚锚点
- 已被定为正式资产的 TOS 工具链

## 本轮清理范围

只处理已经被确认不会参与正式运行、不会参与回滚、也不会作为后续阶段输入的对象：

- 本机临时备份目录 `/tmp/a_machine_backups`
- 本机临时上传包 `/tmp/phase5_web_runtime.tgz`
- 仓库中的 `.DS_Store`
- A 机器候选 web runtime 中由 macOS 上传带入的 `._*` 资源叉文件

## 已执行动作

### 1. 本机残留清理

- 删除 `/tmp/a_machine_backups`
- 删除 `/tmp/phase5_web_runtime.tgz`
- 删除仓库中的 `.DS_Store`

结果：

- 本机不再保留阶段 2 和阶段 5 的失败中间物
- 仓库工作树不再带 Finder 垃圾文件

### 2. A 机器候选 runtime 清理

对以下目录递归删除所有 `._*` 文件：

- `/home/malin/website_aicut_prod/web`

结果：

- 候选 web runtime 中不再包含 macOS 资源叉垃圾文件
- 清理后再次扫描，剩余 `._*` 文件数量为 `0`

## 明确未清理的对象

这些对象仍被定义为正式保留或过渡保留，因此本轮不动：

- `127.0.0.1:3000` 旧前端线
- `192.168.92.197:3001` 当前正式前端线
- `release_0415_slot`
- `website_aicut_api_1`
- `release0415_api`
- `release0415_scheduler`
- `release0415_worker`
- `pg-f10`
- `a-machine-phase5-*` 候选容器
- `website_aicut_git`
- `website_aicut_repo.git`
- `/home/malin/website_aicut_prod/backups/*`
- `/home/malin/website_aicut_prod/tools/tos_uploader`

原因：

- 这些对象要么仍承载正式流量
- 要么仍是阶段 5/阶段 6 的输入
- 要么仍然承担回滚锚点职责

## 验证

### 本机

- `/tmp/a_machine_backups` 已不存在
- `/tmp/phase5_web_runtime.tgz` 已不存在
- 仓库根目录与一级子目录中的 `.DS_Store` 已清空

### A 机器候选线

- `http://127.0.0.1:3301/login` 返回 `200`
- 页面仍能命中 `营销视频剪辑智能体`
- `/home/malin/website_aicut_prod/web` 中剩余 `._*` 文件数量为 `0`

### A 机器正式线

- `https://xiaomajianji.cn/login` 返回 `200`

## 结论

在进入阶段 6 前，本轮还能安全处理的纯垃圾文件和失败中间物已经清掉。

当前剩余未清理对象不再是“遗漏垃圾”，而是：

- 正式运行面
- 过渡运行面
- 回滚锚点
- 阶段 6 的前置输入

因此，下一步应进入阶段 6，而不是继续扩大删除范围。
