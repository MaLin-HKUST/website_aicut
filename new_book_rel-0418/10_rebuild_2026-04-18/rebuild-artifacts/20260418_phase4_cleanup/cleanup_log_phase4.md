# 阶段 4 清理日志

阶段：`20260418_phase4_cleanup`

执行时间：

- 北京时间 2026-04-18 夜间

## 本阶段输入

- 阶段 1 快照：
  - `docker_ps_before.txt`
  - `docker_images_before.txt`
- 阶段 2 备份锚点：
  - `backup/a-machine/pre_rebuild/pre_rebuild_20260418_224329`
- 阶段 3 目标运行面：
  - `target_topology.md`
  - `service_ownership_matrix.md`
  - `phase3_decision_record.md`

## 本阶段执行范围

本阶段只处理“明显无主且不影响回滚”的对象：

- `Created` 状态测试容器
- `Exited` 状态测试容器
- `<none>` dangling 镜像

本阶段明确不处理：

- `release_0415_slot`
- 旧 `3000/8000` 线
- SQLite 数据目录
- 当前 nginx 正式配置
- A 机器上的过渡 Worker 运行面
- `/tmp/tos_uploader_runtime`

## 实际执行动作

### 1. 删除无主测试容器

删除了 22 个 `Created/Exited` 容器：

- `tender_black`
- `pedantic_faraday`
- `postgres16`
- `fervent_ardinghelli`
- `quirky_meninsky`
- `festive_gagarin`
- `charming_hertz`
- `infallible_goldberg`
- `lucid_rhodes`
- `api-test`
- `keen_cartwright`
- `objective_colden`
- `awesome_wiles`
- `elated_sammet`
- `nifty_pasteur`
- `elegant_agnesi`
- `intelligent_tu`
- `festive_taussig`
- `great_williams`
- `charming_faraday`
- `stoic_robinson`
- `tmp_apitest_1`

执行输出记录：

- `docker_rm_output.txt`

### 2. 清理 dangling 镜像

执行 `docker image prune -f`，删除 dangling 镜像并回收空间：

- 回收空间：`619MB`

执行输出记录：

- `docker_image_prune_output.txt`

## 清理前后对比

### 容器数量

- 清理前：`27`
- 清理后：`5`
- 差值：`-22`

对应清单：

- `docker_ps_before.txt`
- `docker_ps_after.txt`

### 镜像数量

- 清理前：`27`
- 清理后：`16`
- 差值：`-11`

对应清单：

- `docker_images_before.txt`
- `docker_images_after.txt`

## 清理后保留的运行中容器

清理后 A 机器仍保留以下 5 个运行中容器：

- `release0415_worker`
- `release0415_api`
- `release0415_scheduler`
- `pg-f10`
- `website_aicut_api_1`

这些对象仍承担正式或过渡职责，未在本阶段触碰。

## 验证结果

### 1. 正式/过渡主链路容器仍在

`docker_ps_after.txt` 显示 5 个运行中容器全部保留。

### 2. 公网登录入口仍可响应

登录页 HTTP 检查结果记录在：

- `login_http_check.txt`

验证目标：

- `https://xiaomajianji.cn/login` 在阶段 4 清理后仍返回成功响应

### 3. 回滚锚点仍在

本阶段未删除以下对象：

- 阶段 2 的 TOS 备份锚点
- SQLite 数据目录
- 当前 nginx 配置
- `release_0415_slot`
- 过渡 Worker 运行面
- `/tmp/tos_uploader_runtime`

## 本阶段结论

阶段 4 已完成最安全子集：

- 清理了所有明显无主的测试容器
- 清理了 dangling 镜像
- 没有影响 A 机器当前正式流量和回滚锚点

当前结果是：

- A 机器不再继续扩散历史测试运行面
- 但旧主站线、旧前端线、过渡 Worker 线、slot 目录仍保留，留待后续阶段按重建步骤处理
