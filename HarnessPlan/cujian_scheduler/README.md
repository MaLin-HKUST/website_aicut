# 粗剪 Smart Cut 调度 Harness

这个目录是 Smart Cut 调度专项的 Harness 工位，用来管理：

- 业务任务与调度任务接入计划
- Fake TOS 集成回归
- 真实 TOS 上线验收
- 清理与执行记录

## 标准 artifact

- `app_spec.txt`
- `feature_list.json`
- `claude-progress.txt`
- `init.sh`
- `README.md`
- `case_catalog.yaml`
- `reports/RESULT_TEMPLATE.md`
- `run_release_gate.py`

## 目录

```text
cujian_scheduler/
├── app_spec.txt
├── feature_list.json
├── claude-progress.txt
├── init.sh
├── README.md
├── case_catalog.yaml
├── run_release_gate.py
├── configs/
├── scripts/
├── cases/
│   ├── auto/
│   ├── fake_tos/
│   └── real_tos/
└── reports/
```

## 固定路径

- 实施计划：
  - `/Users/malin13/Documents/trae_projects/website_aicut/doc/cujiian/粗剪的调度的测试/粗剪SmartCut调度实施计划.md`
- 真实数据验收清单：
  - `/Users/malin13/Documents/trae_projects/website_aicut/doc/cujiian/粗剪的调度的测试/真实数据上线验收测试用例清单.md`
- 真实数据执行记录：
  - `/Users/malin13/Documents/trae_projects/website_aicut/doc/cujiian/粗剪的调度的测试/真实数据上线验收执行记录表.md`
- 真实 worker 镜像 tar：
  - `/Volumes/XIAOMA-A-1T/docker_hub/play_gound/website_aicut-smart_cut_worker_latest.tar.gz`
- Fake TOS 根目录：
  - `/Volumes/XIAOMA-A-1T/docker_hub/FakeTos`

## 使用方式

```bash
cd /Users/malin13/Documents/trae_projects/website_aicut/HarnessPlan/cujian_scheduler

./init.sh status
./init.sh repo-check
./init.sh smoke-test
./init.sh release-gate
./init.sh cleanup
```

## 执行原则

1. 先读 `app_spec.txt` 和 `feature_list.json`
2. 一次只做一个 feature
3. 先写测试，再补实现
4. 任何涉及 Fake TOS 的 run 必须在结束后执行 cleanup
5. 真实数据上线验收必须回填执行记录表
