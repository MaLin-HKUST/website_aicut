# Worker Gateway + A-Scheduler Harness

这个目录只存放 Harness 追踪与验收资产，不存放正式产品代码。

正式代码始终放在主工程：
- `/Users/malin13/Documents/trae_projects/website_aicut/apps`
- `/Users/malin13/Documents/trae_projects/website_aicut/worker`
- `/Users/malin13/Documents/trae_projects/website_aicut/configs`

## 标准 artifacts

- `app_spec.txt`
- `feature_list.json`
- `claude-progress.txt`
- `init.sh`
- `case_catalog.yaml`
- `run_release_gate.py`
- `reports/RESULT_TEMPLATE.md`
- `artifacts/`
- `notes/`

## 工作规则

1. 一次只做一个 feature。
2. 每完成一个 feature，必须验证并提交一次 commit。
3. 不把主工程已有的无关 dirty changes 混进 feature commit。
4. Docker 产物目录固定为：
   `/Volumes/XIAOMA-A-1T/docker_hub/WorkerGateway_and_Ascheduler`
5. 本次版本固定为 `0.0.3`。
6. 镜像 tar 文件名必须包含：
   - 组件名
   - 版本号
   - 时间戳
   - 可选短 commit sha

## 推荐命名

- `a-scheduler_0.0.3_YYYYMMDD_HHMMSS_<shortsha>.tar.gz`
- `worker-gateway_0.0.3_YYYYMMDD_HHMMSS_<shortsha>.tar.gz`

## 使用方式

```bash
cd /Users/malin13/Documents/trae_projects/website_aicut/HarnessPlan/scheduler_AandW

./init.sh status
./init.sh repo-check
./init.sh smoke-test
./init.sh feature-check F02
./init.sh release-gate
```

## 当前阶段

- F01 已完成：Harness Bootstrap
- 下一步：F02 A-Scheduler Runtime Entry And Module Wiring
