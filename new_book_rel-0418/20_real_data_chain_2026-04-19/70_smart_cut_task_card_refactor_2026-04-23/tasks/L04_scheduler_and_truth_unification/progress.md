# L04 进度

## 状态

- 已完成

## 目标

- 收口 API、scheduler、worker 和 task-center 的单一任务真相

## 已完成

- task center 普通用户列表已支持 `company_id` 优先过滤

## 已完成范围

- scheduler 会同步更新对应的 task_run
- task_run 会记录 queued/running/success/failed
- orphaned business task 会自动回收
- task center 普通用户列表已按 `company_id` 优先过滤

## 关联文档

- `../../04_API契约与状态推进.md`
- `../../07_迁移、上线与E2E验收.md`
