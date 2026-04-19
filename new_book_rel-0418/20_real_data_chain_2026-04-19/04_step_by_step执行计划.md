# 04_step_by_step执行计划

本文回答什么问题：

- 真实数据正式链路联调应该按什么顺序执行
- 每一步到底要做什么
- 每一步需要哪些资源
- 什么情况下算这一步做完了
- 用什么方法检查“做完了而且做对了”
- 哪些失败可以重试，哪些失败必须停下

这份文档不是概览，而是本专项的**执行 runbook**。后续 Agent 应把它当作直接操作手册。

## 执行原则

1. 先确认运行面，再跑真实数据，不允许一边猜线上状态一边创建任务。
2. 每一步都要落证据，不允许只保留最后一个成功结果。
3. 每一步都要有完成标准；未达到标准时，不进入下一步。
4. 主路径先走正式链路；主路径失败时再走文档允许的 fallback。
5. 如果问题已经影响正式运行面，优先回滚，不继续联调。

## 统一输入资源

以下资源贯穿整个 runbook，执行前应全部确认可用：

### 文档资源

- `../基础网络信息和账号信息.md`
- `../10_rebuild_2026-04-18/11_2026-04-19_当前系统状态.md`
- `../10_rebuild_2026-04-18/12_2026-04-19_当前Release与证据索引.md`
- `./02_真实数据清单.md`
- `./05_证据清单与产物目录.md`
- `./07_失败处理与回滚条件.md`

### 本地样本资源

- 视频主样本：`/Volumes/XIAOMA-A-1T/wei_videodb/C2384_reencoded.mp4`
- 参考文案：`/Volumes/XIAOMA-A-1T/wei_videodb/ref.txt`
- 历史大文件：`/Volumes/XIAOMA-A-1T/wei_videodb/C2384.MP4`

### 线上运行面资源

- 正式域名：`https://xiaomajianji.cn`
- A 机器：
  - 正式 web：`127.0.0.1:3301`
  - legacy API：`127.0.0.1:8000`
  - Smart Cut API：`127.0.0.1:18001`
  - PostgreSQL：`127.0.0.1:55433`
- Worker：
  - `worker1-phase6-gateway`
  - tunnel：`127.0.0.1:65433 -> A:55433`
  - tunnel：`127.0.0.1:61001 -> A:18001`

### 工具资源

- `ssh`
- `scp`
- `git`
- `curl`
- `ffprobe`
- `docker`
- TOS 正式 SDK / uploader
- `aicut2602/libs/tos_uploader`

## 统一产出规则

每次执行都必须新建一个独立目录：

- `new_book_rel-0418/20_real_data_chain_2026-04-19/artifacts/<timestamp>_real_data_run/`

本文后面每一步引用的证据文件，都默认写入这个目录。

## 阶段概览

本 runbook 固定分为 12 步：

0. 确认前置状态
1. 固定真实样本
2. 建立本轮 artifacts
3. 创建新业务任务
4. 上传真实样本
5. 运行 analyze
6. 运行 preview
7. 运行 finalize
8. 校验最终产物
9. 落档并回写当前状态文档
10. 把真实数据证据转入后续热补收口
11. 对真实任务执行 Playwright UI 观测验收

---

## Step 0：确认前置状态

### 目标

确认当前线上正式运行面仍然与 `11` / `12` 文档一致，避免在漂移环境上跑真实数据。

### 需要的资源

- `../基础网络信息和账号信息.md`
- `../10_rebuild_2026-04-18/11_2026-04-19_当前系统状态.md`
- `../10_rebuild_2026-04-18/12_2026-04-19_当前Release与证据索引.md`
- A 机器 SSH
- Worker SSH

### 要做什么

1. SSH 到 A 机器，核对当前运行面：
   - host web on `127.0.0.1:3301`
   - legacy API on `127.0.0.1:8000`
   - candidate API on `18001`
   - candidate PostgreSQL on `55433`
   - candidate Scheduler
2. SSH 到 Worker，核对：
   - `worker1-phase6-gateway` 仍在运行
   - tunnel 仍存在
3. 从本机检查正式域名是否仍由当前正式 web 返回：
   - `/login`
   - `/welcome`
4. 记录本次检查时的关键 upstream、容器名、端口状态。

### 本步产物

- `preflight_a_machine.txt`
- `preflight_worker.txt`
- `preflight_domain.txt`

### 做到什么算完成

以下条件同时满足才算完成：

- A 机器运行面与 `11_当前系统状态.md` 描述一致
- Worker 与 tunnel 存活
- `xiaomajianji.cn` 仍指向当前正式 web 链路
- 未发现新的未知运行面替代原链路

### 怎么检查做完了做对了

至少验证：

- A 机器容器或进程清单与文档一致
- Worker 容器清单与文档一致
- 域名页面关键标记仍正确

### 失败分叉

- 如果只是某个辅助进程重启了但链路没变，修复后重做 Step 0。
- 如果正式链路已经漂移，停止本专项，先更新 `11` / `12` 再决定是否继续。

---

## Step 1：确认真实样本可读并固定样本版本

### 目标

把本轮真实输入固定下来，避免后续联调时“样本偷偷变了”。

### 需要的资源

- `/Volumes/XIAOMA-A-1T/wei_videodb/C2384_reencoded.mp4`
- `/Volumes/XIAOMA-A-1T/wei_videodb/ref.txt`
- `ffprobe`

### 要做什么

1. 验证视频文件可读。
2. 验证文案文件可读。
3. 读取：
   - 视频文件大小
   - 视频时长、分辨率、编码信息
   - 文案字节数和字符数
4. 写入样本信息文件，固定本轮输入。

### 本步产物

- `sample_info.txt`
- `sample_ffprobe.txt`
- `sample_text_preview.txt`

### 做到什么算完成

以下条件同时满足才算完成：

- `C2384_reencoded.mp4` 可读
- `ref.txt` 可读
- 已记录视频基础元信息
- 已记录文案长度
- 本轮固定采用的样本路径已写入 artifacts

### 怎么检查做完了做对了

至少验证：

- `test -r` 通过
- `ffprobe` 返回非空基础信息
- `wc -c` 和字符统计可读
- `sample_info.txt` 中明确写着本轮主样本路径

### 失败分叉

- 如果样本盘未挂载或不可读，修挂载，不进入 Step 2。
- 如果 `ffprobe` 本机不可用，可以先记录文件大小并继续，但要在 `summary.md` 里注明样本元信息采集不完整。

---

## Step 2：建立本轮 artifacts 目录

### 目标

为本轮运行建立唯一证据目录，后续所有过程文件都写进这里。

### 需要的资源

- 本专项目录写权限
- 当前时间戳

### 要做什么

1. 新建本轮运行目录：
   - `artifacts/<timestamp>_real_data_run/`
2. 预创建或约定本轮证据文件名。
3. 写入运行上下文文件：
   - 当前 operator / agent
   - 当前 git commit
   - 当前 API 基址
   - 当前 nginx upstream

### 本步产物

- 运行目录本身
- `run_context.txt`
- `api_base.txt`
- `nginx_upstream.txt`

### 做到什么算完成

以下条件同时满足才算完成：

- 新目录存在
- 后续证据文件命名已经固定
- 本轮上下文已写入

### 怎么检查做完了做对了

至少验证：

- 目录存在
- `run_context.txt` 已包含时间戳和当前 commit
- `api_base.txt` / `nginx_upstream.txt` 非空

### 失败分叉

- 如果目录创建失败，先解决本地路径或权限，不进入 Step 3。

---

## Step 3：创建真实数据业务任务

### 目标

创建一个新的业务任务，确保这轮不是复用旧任务。

### 需要的资源

- 当前正式 API 入口
- 用户认证态或可用 token/cookie

### 要做什么

1. 调用：
   - `POST /api/smart-cut/tasks`
2. 保存原始响应。
3. 提取并记录：
   - `task_id`
4. 立即读取一次任务详情，确认新任务已落库。

### 本步产物

- `create.json`
- `task_id.txt`
- `task_detail_after_create.json`

### 做到什么算完成

以下条件同时满足才算完成：

- 新任务创建成功
- 取得新的 `task_id`
- 任务详情接口可读到该任务
- 新任务 ID 不等于历史 mock/phase7 任务 ID

### 怎么检查做完了做对了

至少验证：

- `create.json` 返回成功
- `task_id.txt` 非空
- `task_detail_after_create.json` 中能查到同一个 `task_id`

### 失败分叉

- 如果创建失败是认证问题，修认证后重试 Step 3。
- 如果创建失败是正式 API 运行面异常，停止本专项，优先检查正式链路。

---

## Step 4：上传真实样本

### 目标

把真实视频和真实文案挂到本轮业务任务上，让任务进入可 analyze 状态。

### 需要的资源

- 本轮 `task_id`
- `C2384_reencoded.mp4`
- `ref.txt`
- 正式 API
- 必要时的 TOS 直传工具链

### 要做什么

#### 主路径

1. 调用：
   - `POST /api/smart-cut/tasks/{task_id}/upload-direct`
2. 使用真实视频和真实文案作为上传输入。
3. 读取一次任务详情，确认状态变化。

#### fallback 路径

仅当主路径失败时执行：

1. 保存主路径失败响应。
2. 调用：
   - `upload-prepare`
3. 用正式 TOS SDK / uploader 直接上传对象。
4. 调用：
   - `upload-complete`
5. 再读任务详情确认状态。

### 本步产物

- `upload.json`
- `task_detail_after_upload.json`
- 主路径失败时额外保存：
  - `upload_direct_error.json`
  - `upload_prepare.json`
  - `upload_complete.json`
  - `tos_upload_result.json`

### 做到什么算完成

以下条件同时满足才算完成：

- 任务进入 `ready_analyze`
- 视频输入和文案输入都已关联到本轮任务
- TOS 中存在输入对象
- 证据中能够区分本次用了主路径还是 fallback 路径

### 怎么检查做完了做对了

至少验证：

- `upload.json` 或 fallback 组合响应显示成功
- `task_detail_after_upload.json` 中任务状态是 `ready_analyze`
- `tos_objects.txt` 中能查到本轮输入对象 key

### 失败分叉

- 如果主路径失败但 fallback 成功，本轮继续，但必须在总结中记为“主路径失败，fallback 通过”。
- 如果 fallback 也失败，停止本轮，不进入 Step 5。

---

## Step 5：运行 analyze

### 目标

验证 Worker 能消费真实数据 analyze 任务，并把真实 analyze 产物写回 TOS 和任务状态。

### 需要的资源

- `task_id`
- 当前 Worker 在线
- 当前 PostgreSQL / Scheduler 正常
- 当前 TOS 可读写

### 要做什么

1. 调用：
   - `POST /api/smart-cut/tasks/{task_id}/analyze`
2. 保存 analyze 响应。
3. 轮询任务详情，直到：
   - 成功进入 `waiting_user + user_select`
   - 或超时 / 失败
4. 同步抓 Worker 日志。
5. 同步列出本轮 analyze TOS 产物。

### 本步产物

- `analyze.json`
- `analyze_complete.json`
- `task_poll_analyze.txt`
- `worker_logs_analyze.txt`
- `tos_objects_after_analyze.txt`

### 做到什么算完成

以下条件同时满足才算完成：

- 任务最终进入：
  - `status = waiting_user`
  - `current_stage = user_select`
- Worker 日志里出现本轮 analyze 任务
- TOS 中出现 analyze 产物

### 怎么检查做完了做对了

至少验证：

- `analyze_complete.json` 中状态正确
- `tos_objects_after_analyze.txt` 中至少有：
  - `asr.json`
  - `script.json`
  - `delay_cuts.json`
  - `audio_a.mp3`
- `worker_logs_analyze.txt` 中出现本轮 `task_id` 或调度任务 ID

### 失败分叉

- 如果只是轮询超时但后台仍在跑，继续观察，并保留本次证据。
- 如果 TOS 产物缺失、Worker 未消费、或调度状态异常，停止本轮，不进入 Step 6。

---

## Step 6：运行 preview

### 目标

验证真实 analyze 结果可以进入试听链路，生成新的试听产物和新的 edit 状态。

### 需要的资源

- `task_id`
- analyze 后可用脚本：
  - `current_edited_script` 或 `analyze_script`

### 要做什么

1. 从 analyze 完成后的任务详情中提取脚本。
2. 调用：
   - `POST /api/smart-cut/tasks/{task_id}/preview`
3. 轮询任务详情直到 preview 完成。
4. 提取并记录新的：
   - `active_edit_id`
5. 抓 Worker 日志和 TOS preview 产物清单。

### 本步产物

- `preview.json`
- `preview_complete.json`
- `active_edit_id.txt`
- `task_poll_preview.txt`
- `worker_logs_preview.txt`
- `tos_objects_after_preview.txt`

### 做到什么算完成

以下条件同时满足才算完成：

- preview 完成
- 任务再次进入：
  - `status = waiting_user`
  - `current_stage = user_select`
- 生成新的 `active_edit_id`
- TOS 中出现 preview 音频

### 怎么检查做完了做对了

至少验证：

- `preview_complete.json` 状态正确
- `active_edit_id.txt` 非空
- `tos_objects_after_preview.txt` 中存在 preview 对象
- `worker_logs_preview.txt` 中能对应本轮 preview

### 失败分叉

- 如果 preview 响应成功但没生成新的 `active_edit_id`，视为失败，不进入 Step 7。
- 如果只是 Worker 时序抖动，可重试一次 preview；重试必须新建失败记录并说明原因。

---

## Step 7：运行 finalize

### 目标

验证真实数据能够跑完整个 Smart Cut 输出阶段，最终生成可追溯的视频结果。

### 需要的资源

- `task_id`
- `active_edit_id`
- 当前 Worker finalize 环境

### 要做什么

1. 调用：
   - `POST /api/smart-cut/tasks/{task_id}/finalize`
2. 使用本轮最新 `active_edit_id`。
3. 轮询任务详情直到：
   - `success + complete`
   - 或失败 / 超时
4. 抓 Worker finalize 日志。
5. 列出 finalize 后 TOS 产物。

### 本步产物

- `finalize.json`
- `final_success.json`
- `task_poll_finalize.txt`
- `worker_logs_finalize.txt`
- `tos_objects_after_finalize.txt`

### 做到什么算完成

以下条件同时满足才算完成：

- 任务进入：
  - `status = success`
  - `current_stage = complete`
- `final_video_url` 存在
- TOS 中存在最终视频对象

### 怎么检查做完了做对了

至少验证：

- `final_success.json` 状态正确
- `final_success.json` 或任务详情中有 `final_video_url`
- `tos_objects_after_finalize.txt` 中存在最终视频 key
- `worker_logs_finalize.txt` 中出现 finalize 执行记录

### 特殊判定

- 如果因 `ffprobe` 缺失走降级路径，但最终视频生成成功：
  - 这一步记为 `degraded pass`
  - 可以继续到 Step 8
  - 但必须在总结中写明“环境未完全达标”

### 失败分叉

- 如果最终视频未生成，停止本轮，不进入 Step 8。
- 如果只是环境降级但功能通过，可继续，但后续必须进入收口项。

---

## Step 8：下载或校验最终结果

### 目标

证明最终产物是真实存在的，不只是数据库里写回了一个 URL。

### 需要的资源

- `final_video_url`
- TOS 可访问能力

### 要做什么

1. 优先做对象存在性校验：
   - HEAD
   - 或 TOS list / stat
2. 如链路允许，做一次实际下载或部分下载。
3. 记录：
   - 最终对象 key
   - 对象大小
   - 返回码

### 本步产物

- `download_check.txt`
- `final_object_stat.txt`

### 做到什么算完成

以下条件同时满足才算完成：

- 最终对象能被确认存在
- 至少拿到一项强证据：
  - HEAD 200
  - TOS stat 成功
  - 实际下载成功

### 怎么检查做完了做对了

至少验证：

- `download_check.txt` 非空
- 能明确写出最终对象 key 和校验结果

### 失败分叉

- 如果任务状态成功但对象不存在，视为链路失败，不进入 Step 9。

---

## Step 9：落档与回写当前状态文档

### 目标

把这轮真实数据闭环固化成可复查的事实，而不是只停留在命令行输出。

### 需要的资源

- 本轮 artifacts 全部文件
- 本轮 `task_id`
- 调度任务 ID
- `active_edit_id`
- 最终 TOS key
- Worker 名称

### 要做什么

1. 写 `summary.md`，明确：
   - 本轮是否通过
   - 是否为真实数据
   - 是否走了 fallback
   - 是否存在环境降级
2. 更新：
   - `../10_rebuild_2026-04-18/11_2026-04-19_当前系统状态.md`
   - `../10_rebuild_2026-04-18/12_2026-04-19_当前Release与证据索引.md`
3. 如需要，再新增一份本轮真实数据运行报告。

### 本步产物

- `summary.md`
- 对 `11` / `12` 的文档更新
- 可选：
  - `real_data_run_report.md`

### 做到什么算完成

以下条件同时满足才算完成：

- 本轮 artifacts 完整
- `summary.md` 已写
- `11` 和 `12` 已同步这轮真实数据结果

### 怎么检查做完了做对了

至少验证：

- `summary.md` 包含：
  - 样本路径
  - 任务 ID
  - 调度任务 ID
  - `active_edit_id`
  - `final_video_url`
  - 最终对象 key
  - 结论 `pass / blocked / degraded`
- `11` / `12` 文档中可检索到这轮任务信息

### 失败分叉

- 如果任务跑通但文档没更新，这轮不能算完整完成。

---

## Step 10：把真实数据证据转入热补收口和发布收口

### 目标

把本轮真实数据证据变成下一轮代码开发和发布收口的输入。

### 需要的资源

- 本轮 `summary.md`
- `06_热补收口与发布收口.md`
- 当前热补事实

### 要做什么

1. 根据本轮结果，明确后续收口事项：
   - `upload-direct` 是否仍有主路径问题
   - `apps/services/tos_service.py` 是否仍是热补
   - `apps/api/routes/tasks.py` 是否仍是热补
   - Worker 是否仍缺 `ffprobe`
2. 把后续动作写进文档，不要只留在聊天记录里。

### 本步产物

- 更新后的 `06_热补收口与发布收口.md`
- 如有必要，新增“下一轮开发待办”文档

### 做到什么算完成

以下条件同时满足才算完成：

- 已明确下一轮是：
  - 继续代码开发
  - 还是已达到可验收状态
- 后续收口动作已文档化

### 怎么检查做完了做对了

至少验证：

- 文档里明确写出这轮真实数据结果如何影响下一轮开发
- 不再需要依赖当前对话记忆来决定后续做什么

---

## Step 11：对真实任务执行 Playwright UI 观测验收

### 目标

验证正式站已经能对一条真实任务展示正确的试听和下载区域，不再只停留在 API / TOS 证据层。

### 需要的资源

- `apps/web/tests/rel0415-smart-cut-real-task.spec.ts`
- 正式站上可用的真实任务 ID
- Playwright 浏览器运行环境

### 要做什么

1. 准备 `PLAYWRIGHT_REAL_DATA_TASK_ID`
2. 指向正式域名运行 Playwright：
   - `PLAYWRIGHT_BASE_URL=https://xiaomajianji.cn`
   - `PLAYWRIGHT_SKIP_WEBSERVER=1`
3. 验证：
   - `/tasks` 页面可打开
   - `/smart-cut/<task_id>` 可打开
   - 试听播放器可见
   - 下载区域可见

### 本步产物

- `playwright_real_task_ui_check.txt`

### 做到什么算完成

以下条件同时满足才算完成：

- Playwright 用例返回 `passed`
- 用例针对的是正式站上的真实任务，不是 mock task
- 产出文件已写入本轮 artifacts 目录

### 怎么检查做完了做对了

至少验证：

- `playwright_real_task_ui_check.txt` 中显示 `1 passed`
- 用例里使用的任务 ID 与本轮真实任务或已确认成功的真实任务一致

### 失败分叉

- 如果失败是浏览器环境缺失，先补 Playwright 浏览器，不改业务代码。
- 如果失败是 UI 选择器漂移，先核对正式页面结构，再调整用例，不要误判为后端链路失败。
- 如果失败是任务本身没有成功态或没有下载区域，回到前面的业务链路步骤继续排查。

---

## 一次完整运行的判定标准

只有同时满足下列条件，这次真实数据联调才算“完整通过”：

1. Step 0 到 Step 9 全部完成
2. 使用的是固定真实样本：
   - `C2384_reencoded.mp4`
   - `ref.txt`
3. 新任务不是历史 mock 任务
4. `upload-direct` 主路径成功，或者 fallback 成功且已记录
5. analyze / preview / finalize 三段都通过
6. Worker 日志能对应本轮任务
7. TOS 中存在本轮完整对象链
8. 最终视频对象存在且已校验
9. 文档与证据全部落档
10. Playwright UI 观测验收通过

## 不允许的做法

- 不允许跳过 Step 0 直接上传真实数据
- 不允许只保存 `final_success.json`，不保存过程文件
- 不允许任务失败后覆盖上一次 artifacts
- 不允许因为主路径失败就直接宣布整条链路失败，而不尝试文档允许的 fallback
- 不允许在未完成真实数据闭环前，提前宣告“热补已经可以收口”

## 对 Agent 的直接指令

- 执行顺序不能颠倒。
- 每一步没达到完成标准，就不要进入下一步。
- 每一步都要留下可复查证据。
- 如果失败已经影响正式运行面，停止本专项，先回到 `10_rebuild_2026-04-18/` 的回滚手册。
