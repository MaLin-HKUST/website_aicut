# rel0415 Acceptance Current Status

## Grounded facts

- The implementation harness already exists under `HarnessPlan/rel0415`.
- This new harness is only for the last acceptance round.
- Recorded real-data paths still exist in:
  - `tests/test_cujiian/manual_case_config.json`
- The currently recorded paths are:
  - video: `/Volumes/XIAOMA-A-1T/wei_videodb/C2384.MP4`
  - reference: `/Volumes/XIAOMA-A-1T/wei_videodb/ref.txt`

## What this harness must prove

1. Playwright E2E exists for the live 0415 flow
2. Real data is actually used
3. Task queue rendering/status/download are validated
4. Queue behavior is explicitly checked
5. A final verdict is written strongly enough to decide whether 0415 is ready

## Next move

- `A02` 已完成：
  - `/Volumes/XIAOMA-A-1T/wei_videodb/C2384.MP4` 可读
  - `/Volumes/XIAOMA-A-1T/wei_videodb/ref.txt` 可读
  - 当前记录数据集仍可用于最终验收
- `A03` 已完成：
  - Playwright live-route suite 已在 A-machine 上执行
  - `/welcome` `/smart-cut` `/tasks` `/tts` `/admin/tasks` 全部通过
- `A04: Playwright Smart Cut End To End`
- `A05` 已完成：
  - 使用真实样本 `C2384_reencoded.mp4 + ref.txt`
  - 部署侧 analyze 已成功
- `A06` 已完成：
  - 真实数据 preview / finalize 最终跑到 `success`
  - 最终产物 key 已写回任务详情
- `A07` 已完成：
  - 任务中心 user/admin 两侧都验证了状态与下载字段
- `A08` 已完成：
  - 多任务并发创建已验证
  - task-center early snapshot 已捕获 `queued` 和 `queue_position`
- `A04` 已完成：
  - A-machine live Playwright Smart Cut E2E 已通过
  - 过程中修复了 `3001` Next web slot 缺失 `/.next/static` 的部署问题
  - 浏览器已验证任务页 hydration、preview、finalize 和任务中心跳转
- 当前 acceptance 进入 `A09`：
  - 重跑 release gate
  - 生成最终 verdict
  - 写 merge-back checklist
