# Progress

当前阶段：

- `CQ01-CQ05` 已在 repo 代码层完成并部署到 live API / frontend
- `CQ06` 已完成：公司级可见性和同公司双任务 `running -> queued -> running` 已拿到 live 证据
- `CQ07` 仍未完成完整 fresh 验证

已完成：

- 新建专项包
- 记录调试与部署过程
- `company_id` 已接入模型、schema、task center 和前端查询
- API 回归通过
- live API 已部署到 `18002`
- live frontend production runtime 已部署到 `3301`
- PostgreSQL `smart_cut_tasks.company_id` 已对齐到 live schema
- 新建同公司第二测试账号：
  - `rbzj_queue2 / 123456`
- live 验证结果：
  - `rbzj` 和 `rbzj_queue2` 都能看到公司 `日标住建` 的同一任务队列
  - `zhangyongqiang`（公司 `小马AI`）看不到 `日标住建` 的任务
  - 同公司两条正式任务进入任务中心后，第一条显示 `执行中`，第二条显示 `排队中`
  - 修复 scheduler 对 `POST + terminal task` 的竞态回收后，第一条完成后第二条已自动从 `排队中` 切到 `执行中`

待完成：

- 跑 `CQ07` 的 fresh 端到端验证
- 决定是否保留测试账号 `rbzj_queue2`

当前判断：

- 单 worker 底层继续全局 FCFS
- 页面只展示公司视角队列
- 之前卡住第二条的根因已经定位并修复：
  - worker 可能在任务终态后把设备重新写回 `POST + old current_task_id`
  - scheduler 现在会在新一轮开始前回收“指向终态调度任务”的陈旧设备占用
- 当前剩余工作不在公司级队列本身，而在是否继续保留测试数据与测试账号
