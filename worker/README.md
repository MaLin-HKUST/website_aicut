# Smart Cut Worker

这组文件用于“智能剪口播气口”的第一层容器测试，不接入现有 `web/api` 服务。

## 目的

- 提供一个最小 worker 容器
- 在容器内满足 `online_version` 的路径假设
- 直接执行 `tests/test_cujiian` 这套后端联调脚本

## 关键路径

- 容器内算法库：`/app/aicut2602`
- 容器内测试脚本：`/app/website_aicut/tests/test_cujiian`
- 容器内工作目录：`/data/smart-cut`

## 使用方式

构建并启动容器：

```bash
docker compose -f docker-compose.smart-cut.yml up --build -d
```

进入容器：

```bash
docker compose -f docker-compose.smart-cut.yml exec smart_cut_worker bash
```

运行整套第一层测试：

```bash
docker compose -f docker-compose.smart-cut.yml exec smart_cut_worker \
  run-manual-cujian-test \
  /app/website_aicut/tests/test_cujiian/manual_case_config.example.json
```

也可以逐步执行：

```bash
docker compose -f docker-compose.smart-cut.yml exec smart_cut_worker bash
cd /app/website_aicut
python tests/test_cujiian/step01_analyze.py --config tests/test_cujiian/manual_case_config.example.json
```

## 注意

- 这个 compose 文件会把宿主机的 `/Volumes` 只读挂到容器里，用来兼容当前测试配置中的原始素材路径。
- 如果素材不在 `/Volumes` 下，需要按相同思路增加对应宿主机目录挂载。
- `./tmp/smart-cut-data` 是容器内 `/data/smart-cut` 的宿主机映射目录，用于查看中间产物。
