# Fake TOS Cases

这一层用于对象存储交互逻辑回归，不依赖真实云 TOS。

Fake TOS 固定路径：

- 宿主机：`/Volumes/XIAOMA-A-1T/docker_hub/FakeTos`
- 容器内：`/fake-tos`

推荐覆盖：

- `P0-E2E-001` 到 `P0-E2E-004`
- `P0-REC-001` 到 `P0-REC-005`
- `P0-ERR-001`、`P0-ERR-002`、`P0-ERR-004`、`P0-ERR-005`
- `P0-TOS-001` 到 `P0-TOS-004`

注意：

- 每次执行必须使用独立 `run_id`
- 结束后必须执行 cleanup
