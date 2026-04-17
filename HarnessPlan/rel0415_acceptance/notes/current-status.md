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
