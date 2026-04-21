# 60_smart_cut_company_queue_2026-04-22

本专项处理两件事：

1. 记录 2026-04-21 到 2026-04-22 这轮 Smart Cut 从部署混乱到 fresh 全链路跑通的调试与上线过程。
2. 把任务中心从用户级可见性升级成公司级可见性，并定义“单 worker 下共享 FCFS、公司内共享队列、跨公司不可见”的正式规则。

阅读顺序：

1. [01_调试与部署过程记录.md](./01_调试与部署过程记录.md)
2. [02_公司级队列与可见性契约.md](./02_公司级队列与可见性契约.md)
3. [03_分段上线与累积E2E计划.md](./03_分段上线与累积E2E计划.md)
4. [task.json](./task.json)
5. [progress.md](./progress.md)
6. [progress.json](./progress.json)

关键结论：

- Smart Cut 当前已在正式站 fresh 跑通一条真实链路：
  - task: `0e7d0b64-503f-453c-9841-f54929274ead`
  - title: `智能剪气口-20260422-003136`
  - final key: `smart-cut/0e7d0b64-503f-453c-9841-f54929274ead/finalize/final_video.mp4`
- 当前下一步不是再修状态机主链，而是补：
  - `company_id` 贯穿到任务模型和任务中心
  - 公司级可见性
  - 单 worker 下的多正式任务排队验证
