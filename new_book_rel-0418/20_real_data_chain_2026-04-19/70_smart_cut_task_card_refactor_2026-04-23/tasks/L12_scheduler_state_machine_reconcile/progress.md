# L12 Smart Cut 调度状态机闭环与仿真矩阵

## 2026-04-26 19:20 BJT

### 任务来源

线上出现 Smart Cut analyze 已完成但任务卡仍停在“正在分析”的状态问题。用户要求不只修一个点，还要把所有正向、页面操作、错误与异常状态组合写成可模拟的调度矩阵，并把任务拆解、过程和结果纳入 codebook 与 git 管理。

### 已确认的坏状态

- `smart_cut_tasks.status = analyzing`
- `scheduler_tasks.status = running`
- `scheduler_tasks.result is not null`
- `smart_cut_devices.status = idle`
- `smart_cut_devices.current_task_id = scheduler_tasks.id`
- worker 日志已显示任务成功完成

### 当前修复方向

- worker 成功后显式把 scheduler task 推到 `post`，不只写 `result`。
- scheduler 增加自愈闭环：`post + result` 和遗留 `running + result` 都可以被闭环。
- 对 `idle + current_task_id` 做语义收口：只有 scheduler task 仍是 `assigned` 时才代表“已分配待领取”，否则要清理或闭环。
- auto-finalize 增加幂等保护，避免重复排 finalize。
- 用数据库状态组合测试覆盖真实用户操作和异常恢复，不启动 Playwright、真实 worker、docker 或算法。

### 分支

`smart-cut-state-machine-reconcile-20260426`

## 2026-04-26 19:40 BJT

### 已完成

- worker 成功结果落库时同步写入 `scheduler_tasks.status=post`。
- scheduler 新增 `reconcile_completed_scheduler_tasks()`，对 `post/result` 和遗留 `running/result` 做闭环。
- analyze 自动 finalize 增加幂等保护，已有活跃 finalize 时复用原 run。
- `_advance_business_task_on_post()` 支持无 device 行的自愈闭环。
- 增加状态组合仿真矩阵文档。

### 验证

```bash
python3 -m pytest tests/test_task_truth_reconcile.py -q
```

结果：`8 passed, 6 warnings in 6.49s`。warnings 是现有 Pydantic v2 deprecation，不是本次改动引入的失败。

## 2026-04-26 19:45 BJT

### 收口

- `task.json` 已把 L12/S1201-S1205 标记为完成。
- `progress.json` 已记录实现、验证和剩余风险。
- 本次不做线上部署、不清理线上任务、不启动 Playwright。

## 2026-04-27 00:20 BJT

### 发布前补丁

SOP preflight 发现生产 `worker1-phase6` 为 `IDLE`，但 `current_task_id` 指向已不存在的 scheduler task，导致 `busy_devices=1`。这会阻止新任务被分配。

已补充：

- `reconcile_stale_device_assignments()`：释放 `IDLE + current_task_id` 且 scheduler task 不存在或非 `assigned` 的 worker。
- 保留合法的 `IDLE + current_task_id + scheduler=assigned`，这是“已分配待领取”状态。
- 新增 2 个回归测试覆盖上述两个分支。

验证：

```bash
python3 -m py_compile worker/core.py apps/scheduler/scheduler_service.py
python3 -m pytest tests/test_task_truth_reconcile.py -q
```

结果：`10 passed, 6 warnings in 1.79s`。
