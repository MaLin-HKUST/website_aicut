# Progress

当前阶段：

- `CQ01-CQ05` 已在 repo 代码层完成并部署到 live API / frontend
- `CQ06` 已完成一半：公司级可见性和同公司双任务 `running -> queued` 已拿到 live 证据
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

待完成：

- 把 `CQ06` 跑到“第一条完成后第二条自动接棒”的最终证据
- 跑 `CQ07` 的 fresh 端到端验证
- 决定是否保留测试账号 `rbzj_queue2`

当前判断：

- 单 worker 底层继续全局 FCFS
- 页面只展示公司视角队列
- 当前剩余阻塞不在公司可见性，而在 finalize 长上传：
  - 第一条排队测试任务的算法子容器已经产出本地 `final_video.mp4`
  - 但 worker gateway 还在 finalize 最后一段上传到 TOS，因此第二条仍保持 `queued`
- 这说明队列策略本身已生效，尚未拿到的是“长上传完成后第二条自动接棒”的最终收口证据
