# SMART-cut Worker 容器分析

> 分析对象：`/Volumes/XIAOMA-A-1T/docker_hub/play_gound/website_aicut-smart_cut_worker_latest.tar.gz`
> 分析时间：2026-04-06

---

## 一、容器基本信息

| 属性 | 值 |
|------|-----|
| **镜像名称** | website_aicut-smart_cut_worker:latest |
| **基础镜像** | Debian Trixie (amd64) |
| **Python版本** | 3.11.15 |
| **工作目录** | `/app` |
| **Entrypoint** | `smart-cut-entrypoint` |
| **默认命令** | `sleep infinity` |
| **所属项目** | website_aicut (docker-compose) |

---

## 二、关键入口文件

### 2.1 Entrypoint 脚本

**位置**：`/usr/local/bin/smart-cut-entrypoint`

```bash
#!/usr/bin/env bash
set -euo pipefail

export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1
export PYTHONPATH="/app/aicut2602:/app/aicut2602/libs/cut_breakpoints/online_version:${PYTHONPATH:-}"

mkdir -p /data/smart-cut

if [ -d /app/website_aicut/tests/test_cujiian ]; then
  mkdir -p /app/website_aicut/tests/test_cujiian/output
  mkdir -p /app/website_aicut/tests/test_cujiian/fake_tos
fi

exec "$@"
```

**关键配置**：
- `PYTHONPATH` 包含两个核心路径：
  - `/app/aicut2602` - 算法库根目录
  - `/app/aicut2602/libs/cut_breakpoints/online_version` - 在线版封装层
- 创建工作目录 `/data/smart-cut`
- 如果存在测试目录，创建 output 和 fake_tos 子目录

### 2.2 手动测试脚本

**位置**：`/usr/local/bin/run-manual-cujian-test`

用于本地手动运行粗剪测试。

---

## 三、容器内目录结构

```
/
├── app/                          # 工作目录（运行时挂载）
│   ├── aicut2602/               # 算法库
│   │   └── libs/
│   │       └── cut_breakpoints/
│   │           └── online_version/   # CX2在线版封装层
│   └── website_aicut/           # 网站服务代码
│       └── tests/
│           └── test_cujiian/    # 粗剪测试目录
├── data/
│   └── smart-cut/               # 任务工作目录
├── usr/local/bin/
│   ├── smart-cut-entrypoint     # 容器入口脚本
│   └── run-manual-cujian-test   # 手动测试脚本
└── tmp/
    └── worker-requirements.txt  # Python依赖（构建时COPY）
```

---

## 四、依赖安装

构建时执行的安装步骤：

1. **系统依赖**：
   ```bash
   apt-get install -y --no-install-recommends bash ffmpeg
   ```

2. **Python依赖**：
   ```bash
   pip install --no-cache-dir -r /tmp/worker-requirements.txt
   ```

**注意**：实际代码（`website_aicut/` 和 `aicut2602/`）不在镜像内，运行时通过**挂载**注入。

---

## 五、FakeTOS 目录

**路径**：`/Volumes/XIAOMA-A-1T/docker_hub/FakeTos`

**当前状态**：空目录

**用途推测**：
- 本地开发/测试时模拟 TOS（对象存储）的目录
- 运行时可能挂载到容器的 `/app/website_aicut/tests/test_cujiian/fake_tos`
- 用于存放测试用的视频、文案等输入文件

---

## 六、运行时挂载映射（推测）

根据 docker-compose 惯例和 entrypoint 逻辑：

| 宿主机路径 | 容器路径 | 说明 |
|-----------|---------|------|
| `~/projects/aicut2602` | `/app/aicut2602` | 算法库代码 |
| `~/projects/website_aicut` | `/app/website_aicut` | 网站服务代码 |
| `~/docker_hub/FakeTos` | `/app/website_aicut/tests/test_cujiian/fake_tos` | 模拟TOS存储 |
| 数据卷或宿主机目录 | `/data/smart-cut` | 任务工作目录 |

---

## 七、关键环境变量

| 变量名 | 值 | 说明 |
|--------|-----|------|
| `PYTHONDONTWRITEBYTECODE` | `1` | 不生成.pyc文件 |
| `PYTHONUNBUFFERED` | `1` | 无缓冲输出 |
| `PYTHONPATH` | `/app/aicut2602:/app/aicut2602/libs/cut_breakpoints/online_version` | Python模块搜索路径 |
| `PATH` | `/usr/local/bin:...` | 包含smart-cut-entrypoint |

---

## 八、与 CX2 开发方案的对应

根据 `cujian_plan_cx2.md` 的设计：

| CX2方案设计 | 容器实际配置 |
|------------|-------------|
| 在线版代码放在 `/app/aicut2602/libs/cut_breakpoints/online_version/` | ✅ PYTHONPATH中已包含 |
| 服务代码放在 `website_aicut/worker/` | ✅ 通过挂载注入 |
| 工作目录 `/data/smart-cut/{task_id}/` | ✅ entrypoint创建基础目录 |
| TOS文件交互 | ❓ FakeTos目录可能用于本地模拟 |

---

## 九、使用方式

### 9.1 启动容器（基础）

```bash
docker run -it --rm \
  -v ~/projects/aicut2602:/app/aicut2602 \
  -v ~/projects/website_aicut:/app/website_aicut \
  -v ~/docker_hub/FakeTos:/app/website_aicut/tests/test_cujiian/fake_tos \
  website_aicut-smart_cut_worker:latest \
  bash
```

### 9.2 运行手动测试

```bash
docker run -it --rm \
  -v ~/projects/aicut2602:/app/aicut2602 \
  -v ~/projects/website_aicut:/app/website_aicut \
  website_aicut-smart_cut_worker:latest \
  run-manual-cujian-test
```

### 9.3 通过 docker-compose

```bash
docker-compose up smart_cut_worker
```

---

## 十、待确认事项

1. **worker/requirements.txt 内容**：需要查看具体的Python依赖
2. **run_manual_cujian_test.sh 内容**：了解手动测试的具体流程
3. **FakeTos 挂载路径**：确认实际 docker-compose.yml 中的挂载配置
4. **任务队列**：确认 Worker 是通过什么机制（Celery/RQ/自定义）消费任务

---

## 十一、快速检索命令

```bash
# 查看镜像配置
docker inspect website_aicut-smart_cut_worker:latest

# 进入容器调试
docker run -it --rm \
  -v ~/projects/aicut2602:/app/aicut2602 \
  -v ~/projects/website_aicut:/app/website_aicut \
  website_aicut-smart_cut_worker:latest \
  bash

# 查看entrypoint
cat /usr/local/bin/smart-cut-entrypoint

# 查看Python路径
python3 -c "import sys; print('\n'.join(sys.path))"
```

---

*本文档基于容器镜像静态分析生成，运行时行为需结合实际挂载的代码和配置确认。*
