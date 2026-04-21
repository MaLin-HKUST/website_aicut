# Progress

当前阶段：

- `CQ01-CQ05` 已在 repo 代码层开始落地
- `CQ06-CQ07` 还未做 live 验证

已完成：

- 新建专项包
- 记录调试与部署过程
- `company_id` 已接入模型、schema、task center 和前端查询
- API 回归通过

待完成：

- 提交当前改动
- 决定是否立即部署到 live API / frontend
- 做双任务排队和公司可见性的真实验证

当前判断：

- 单 worker 底层继续全局 FCFS
- 页面只展示公司视角队列
