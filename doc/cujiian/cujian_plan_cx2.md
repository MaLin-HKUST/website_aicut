# 智能剪口播气口功能开发方案（CX2 可实施版）

## 目标

把“智能剪口播气口”做成一条可上线、可重试、可运维的三阶段任务流：

1. `analyze`：分析原视频，产出可编辑脚本和 `audio_a`
2. `preview`：基于用户修订脚本，重算 `delay_cuts`、`pause_cuts`，产出试听 `audio_b`
3. `finalize`：根据用户选择的输出规格，生成最终视频

核心约束：

- Worker 不阻塞等待用户交互
- `audio_b` 只用于试听，不参与最终视频合成
- `analyze` / `preview` 始终基于原始上传视频
- `normalize` 只在 `finalize` 且仅当用户选择 `1080P竖屏` 时执行
- 输出码率规则必须真正生效：`min(input_bitrate, 12Mbps)`
- 输入视频和最终视频走 TOS，API 不直接承载大文件传输

---

## 一、最终产品规则

### 1.1 用户侧流程

1. 创建任务
2. 前端直传原视频 + 标准文案到 TOS
3. 前端确认上传完成
4. 点击“开始分析”
5. 系统返回带删除建议的脚本和 `audio_a`
6. 用户在前端通过按钮调整删除范围
7. 点击“生成试听”
8. 系统返回 `audio_b`
9. 用户选择输出规格：
   - `原始尺寸`
   - `1080P竖屏`
10. 用户决定是否“投喂本文案给AI”
   - 前端复选框：`投喂本文案给AI`
   - 默认勾选
11. 点击“生成视频”
12. 系统生成最终视频并上传到 TOS
13. 如勾选投喂，则把本次 GroundTruth 数据上传到 TOS 指定路径
14. 前端显示下载视频超链接

### 1.2 输出规格规则

- 选择 `原始尺寸`
  - 不做 normalize
  - 最终视频直接基于原视频剪辑输出

- 选择 `1080P竖屏`
  - 在 `finalize` 阶段先调用 `incoming_video_process`
  - 生成：
    - `normalized_input.mp4`
    - `normalized_input.process.json`
  - 然后基于同一套 cuts 对归一化后视频做最终剪辑

- 最终输出视频码率：
  - `output_bitrate = min(input_bitrate, 12_000_000)`
  - 如果无法可靠探测输入码率，则回退到 `12Mbps`

### 1.3 GroundTruth 投喂规则

- preview 阶段用户修改后的文档视为一个 GroundTruth 样本
- 在文本框边上放复选框：`投喂本文案给AI`
- 默认勾选
- 触发时机：
  - 用户点击“生成视频”之后
  - 且 `finalize` 阶段开始执行时
- 如果勾选，则归档本次样本
- 如果未勾选，则不归档

需要归档的内容：

- 标准文案
- 输入视频 URL / TOS key
- 输入视频 ASR
- 系统输出的 script
- 用户修改后的 script

GroundTruth 存储路径：

```text
cujian_input_data/{company}/{year-month}/cujian_userdata_{timestamp}/
```

用途：

- 后续算法评测
- 算法回归测试
- 各公司定制数据积累

---

## 二、必须修正的历史问题

本方案明确修掉以下问题：

### 2.1 修正路径错误

不再使用模糊的相对 `sys.path.insert(... parent.parent / 'src')`。

统一使用以下路径原则：

- `website_aicut` 是服务编排入口
- `aicut2602` 是算法依赖目录
- Worker 容器内固定挂载：
  - `/app/website_aicut`
  - `/app/aicut2602`

统一导入根：

```python
AI_CUT_ROOT = Path("/app/aicut2602")
WEBSITE_ROOT = Path("/app/website_aicut")
```

然后显式：

```python
sys.path.insert(0, str(AI_CUT_ROOT))
```

所有算法模块都按完整包路径导入，例如：

```python
from libs.cut_breakpoints.src.script_to_delay_cuts import ScriptToDelayCuts
from libs.cut_breakpoints.src.pause_detect import detect_pauses_on_audio_a
from libs.cut_breakpoints.src.time_mapping import TimelineMapper
from libs.cut_breakpoints.src.direct_cutter import DirectCutter
from libs.cut_breakpoints.src.run_raw_cut import normalize_input_video
```

### 2.2 修正 PauseCuts 格式不兼容

当前 `DirectCutter.load_pause_cuts()` 读取格式为：

```json
{
  "cut_segments": [
    {
      "start_time": 1234,
      "end_time": 1567,
      "type": "pause"
    }
  ]
}
```

并且时间单位是毫秒。

所以本方案规定：

- `preview` 阶段内部可使用秒级列表进行计算
- 但供 `finalize` 使用的 `pause_cuts_on_original.json` 必须落盘为 `DirectCutter` 兼容格式：

```json
{
  "cut_segments": [
    {
      "start_time": 1234,
      "end_time": 1567,
      "type": "pause",
      "position": ""
    }
  ]
}
```

### 2.3 修正码率规则无法落地的问题

原 `DirectCutter` 内部 ffmpeg 参数写死，不能满足动态码率要求。

所以本方案不直接改原 `DirectCutter`，而是新增一个在线版封装器：

- `online_version/src/final_video_cutter.py`

职责：

1. 复用 `DirectCutter` 的 cuts 计算逻辑
2. 自己生成 `filter_complex`
3. 自己执行 ffmpeg
4. 支持动态传入：
   - `video_bitrate`
   - `maxrate`
   - `bufsize`

这样既不破坏原代码，又能真正落下输出码率规则。

### 2.4 修正 normalize 元数据缺失

如果选择 `1080P竖屏`，必须同时保存：

- `normalized_input.mp4`
- `normalized_input.process.json`

并把这两个路径/URL 写入任务表，供：

- 失败排查
- 任务重试
- 输出规格追踪

---

## 三、代码组织方案

### 3.1 代码位置

新的在线版代码放在：

```text
/app/aicut2602/libs/cut_breakpoints/online_version/
```

目录建议：

```text
online_version/
├── src/
│   ├── __init__.py
│   ├── analyze_processor.py
│   ├── preview_processor.py
│   ├── finalize_processor.py
│   ├── generate_audio_b.py
│   ├── pause_mapping.py
│   ├── final_video_cutter.py
│   ├── script_formatter.py
│   └── paths.py
├── tests/
│   ├── test_generate_audio_b.py
│   ├── test_pause_mapping.py
│   ├── test_script_formatter.py
│   └── test_finalize_processor.py
└── README.md
```

### 3.2 服务代码位置

任务入队、状态更新、数据库模型仍放在 `website_aicut`：

```text
website_aicut/
├── apps/api/
├── worker/
└── doc/
```

原因：

- `worker` 是网站服务的一部分
- `online_version` 是算法库上的在线封装层
- 两者职责不同，不要混放

---

## 四、三阶段任务设计

## 4.1 analyze

### 输入

- `original_video_url`
- `reference_text_url`

### 处理

Worker 先从 TOS 下载输入文件到本地工作目录：

```text
/data/smart-cut/{task_id}/input/
├── source_video.mp4
└── reference.txt
```

然后直接调用原入口的 A 流程：

```bash
python /app/aicut2602/libs/cut_breakpoints/src/run_raw_cut.py \
  -i <local_source_video> \
  -r <local_reference_text> \
  -o <stage_a_dir> \
  --flow-a
```

### 产物

- `*_ASR.Result.json`
- `*_原文.TXT`
- `*_Script1.txt`
- `*_DelayCutSegments.json`
- `*_audio_a.mp3`

### 返回给前端

- `script`：大括号格式纯文本
- `delete_ranges`
- `audio_a_url`

### 注意

- 不做 normalize
- 不做 pause cut

---

## 4.2 preview

### 输入

- 用户修订后的脚本，大括号格式
- `ASR.Result.json`
- 原始视频（从 TOS 下载到本地，或复用工作目录缓存）

### 处理链路

1. 用用户修订后的脚本重新生成 `edited_delay_cuts`
2. 基于 `edited_delay_cuts` 重新生成 `edited_audio_a`
3. 用 `detect_pauses_on_audio_a()` 生成 `pause_cuts_on_audio_a`
4. 生成 `audio_b`
5. 把 `pause_cuts_on_audio_a` 映射回原视频时间轴
6. 保存一份 `DirectCutter` 可直接读取的 `pause_cuts_on_original.json`

### preview 阶段真实输出

- `edited_delay_cuts.json`
- `edited_audio_a.mp3`
- `pause_cuts_on_audio_a.json`
- `pause_cuts_on_original.json`
- `audio_b.mp3`

### preview 后处理

`audio_b.mp3` 需要上传到 TOS，并把 `audio_b_url` / `audio_b_tos_key` 回写到任务或 edit 记录。

说明：

- `audio_b` 要给前端试听，所以必须可访问
- `audio_a` 不对前端暴露，不要求上传 TOS

### 关键结论

- 最终视频使用：
  - `edited_delay_cuts.json`
  - `pause_cuts_on_original.json`
- 不使用 `audio_b` 参与最终合成

### preview 交互限制

preview 阶段前端不是自由文本编辑器，而是“删除状态编辑器”。

用户只允许通过系统提供的按钮执行两种操作：

1. 添加删除线
2. 反删除线（恢复）

明确限制：

- 不支持自由输入新文字
- 不支持改写正文内容
- 不支持直接删除正文字符
- 正文字符顺序必须保持与 analyze 产出的 script 一致

因此，`edited_script` 的变化只体现在 `{}` 标记范围变化，不体现在正文文本内容变化。

---

## 4.3 finalize

### 输入

- 原始视频 URL
- `edited_delay_cuts.json`
- `pause_cuts_on_original.json`
- `output_mode`

### 逻辑

#### 模式 A：`original`

- 直接用原视频本地副本剪辑

#### 模式 B：`vertical_1080p`

1. 调用 `normalize_input_video()`
2. 保存：
   - `normalized_input.mp4`
   - `normalized_input.process.json`
3. 用归一化后视频做最终剪辑

### finalize 后处理

最终视频生成后必须：

1. 上传 `final_video.mp4` 到 TOS
2. 获取 `final_video_url`
3. 更新数据库任务状态和 TOS key
4. 前端详情接口返回下载链接

如果本次任务勾选了“投喂本文案给AI”，还必须：

5. 生成 GroundTruth JSON
6. 上传到 TOS 的 `cujian_input_data/{company}/{year-month}/.../` 目录路径
7. 把 GroundTruth 的 URL / key 写回任务

### 最终编码规则

1. 先用 `ffprobe` 读取输入视频码率
2. 计算：

```python
output_bitrate = min(input_bitrate, 12_000_000) if input_bitrate else 12_000_000
maxrate = output_bitrate
bufsize = output_bitrate * 2
```

3. 交给在线版 `final_video_cutter.py` 执行 ffmpeg

---

## 五、关键模块设计

## 5.1 `generate_audio_b.py`

### 原则

- `audio_b` 只用于试听
- 不要求映射回原视频
- 优先保证试听边界稳定，不追求无损 copy

### 实现要求

不要用 `-c copy` 直接裁 mp3 再 concat。

改为统一用一次 `filter_complex` 重编码输出，避免：

- 边界不准
- 时长漂移
- mp3 分段拼接兼容问题

建议命令风格：

```bash
ffmpeg -i audio_a.mp3 -filter_complex "<atrim concat表达式>" -c:a mp3 output.mp3
```

如果实现复杂，次选方案是：

- 每段先转 pcm/wav
- 最后统一编码为 mp3

但不要全程 `-c copy`

---

## 5.2 `pause_mapping.py`

职责：

- 接收 `pause_cuts_on_audio_a`
- 接收 `delay_cuts`
- 使用 `TimelineMapper`
- 输出两种格式：

1. 内部秒级列表
2. `DirectCutter` 兼容 JSON

建议暴露两个函数：

```python
def map_pauses_to_original_seconds(...) -> list[dict]:
    ...

def dump_pause_cuts_for_direct_cutter(mapped_pauses_seconds: list[dict], output_path: str) -> str:
    ...
```

第二个函数的输出格式必须是：

```json
{
  "cut_segments": [
    {
      "start_time": 1234,
      "end_time": 1567,
      "type": "pause",
      "position": ""
    }
  ]
}
```

---

## 5.3 `final_video_cutter.py`

### 目的

解决“不能改原 `DirectCutter`，但又要动态码率”的矛盾。

### 方案

新增一个在线版 cutter：

```python
class OnlineFinalVideoCutter:
    def __init__(self, video_path: str): ...
    def load_delay_cuts(self, path: str): ...
    def load_pause_cuts(self, path: str): ...
    def calculate_keep_segments(self): ...
    def save_cut_plan(self, path: str): ...
    def cut(
        self,
        output_path: str,
        *,
        video_bitrate: int,
        maxrate: int,
        bufsize: int,
        preset: str = "veryfast",
        audio_bitrate: str = "192k"
    ): ...
```

### 实现方式

- 直接复用 `DirectCutter` 的 keep_segments 计算思路
- 但 ffmpeg 输出命令由在线版自己控制

这样输出参数就可控：

```bash
-c:v libx264
-b:v <video_bitrate>
-maxrate <maxrate>
-bufsize <bufsize>
```

---

## 5.4 `file_store.py`

### 目的

统一处理 TOS 输入输出，避免对象存储逻辑散落在多个处理器中。

### 建议位置

```text
website_aicut/worker/services/file_store.py
```

### 职责

提供统一接口：

```python
def download_from_tos(url: str, local_path: str) -> str:
    ...

def upload_to_tos(local_path: str, object_key: str) -> dict:
    """
    returns:
    {
      "url": "...",
      "key": "..."
    }
    """
```

### 调用规则

- `analyze` 开始前下载 `original_video_url` 和 `reference_text_url`
- `preview` 结束后上传 `audio_b.mp3`
- `finalize` 完成后上传 `final_video.mp4`
- `finalize` 如果勾选投喂，还要上传 GroundTruth JSON

### 本地缓存硬规则

- 默认每个阶段都优先使用本地 `work_dir`
- 本地缺文件时再从 TOS 回拉
- 若本地文件与数据库记录不一致，以数据库中的 TOS key 为准重新下载

---

## 5.5 `groundtruth_recorder.py`

### 目的

把用户确认后的样本沉淀为后续算法可复用数据。

### 建议位置

```text
/app/aicut2602/libs/cut_breakpoints/online_version/src/groundtruth_recorder.py
```

### 输入

- `company_name`
- `reference_text`
- `original_video_url`
- `original_video_tos_key`
- `asr_result_url`
- `analyze_script`
- `edited_script`
- `task_id`
- `timestamp`

### 输出

输出一个 GroundTruth 目录，并上传到 TOS。

该目录中至少包含以下内容：

```text
cujian_input_data/{company}/{year-month}/cujian_userdata_{timestamp}/
├── reference.txt
├── analyze_script.txt
├── edited_script.txt
├── metadata.json
└── asr_result.json
```

其中：

- `reference.txt`
  - 标准文案
- `analyze_script.txt`
  - 系统输出的 script
- `edited_script.txt`
  - 用户修改后的 script
- `asr_result.json`
  - 输入视频对应的 ASR
- `metadata.json`
  - 输入视频 URL / TOS key、任务 id、公司、时间戳等元数据

`metadata.json` 建议结构：

```json
{
  "task_id": "uuid",
  "company": "company_a",
  "created_at": "2026-04-03T12:00:00+08:00",
  "reference_text": "...",
  "original_video_url": "...",
  "original_video_tos_key": "...",
  "asr_result_url": "...",
  "analyze_script": "...",
  "edited_script": "..."
}
```

### TOS 路径

```text
cujian_input_data/{company}/{year-month}/cujian_userdata_{timestamp}/
```

### 触发规则

- 只在 `finalize` 阶段触发
- 只在 `feed_to_ai=true` 时触发
- GroundTruth 上传失败不应阻塞最终视频生成成功
- 但必须单独记录失败状态，方便后续补偿

---

## 六、处理器设计

## 6.1 `analyze_processor.py`

不要依赖当前工作目录。

应该这样写：

```python
RUN_RAW_CUT = "/app/aicut2602/libs/cut_breakpoints/src/run_raw_cut.py"

cmd = [
    "python",
    RUN_RAW_CUT,
    "-i", video_path,
    "-r", reference_path,
    "-o", output_dir,
    "--flow-a",
]
```

产物路径也不要只靠视频文件名猜，建议：

- 明确传 `-n task_<task_id>`
- 后续所有输出统一以 `task_<task_id>` 为前缀

---

## 6.2 `preview_processor.py`

### 输入

- `edited_script_path`
- `asr_result_path`
- `original_video_path`
- `output_dir`
- `task_id`

### 输出

```json
{
  "edited_delay_cuts_path": "...",
  "edited_audio_a_path": "...",
  "pause_cuts_on_audio_a_path": "...",
  "pause_cuts_on_original_path": "...",
  "audio_b_path": "..."
}
```

### 强约束

- `pause_cuts_on_original_path` 必须是 `DirectCutter` 兼容格式
- `audio_b` 失败不能 silently continue，必须显式失败

---

## 6.3 `finalize_processor.py`

### 输入

- `video_source_path`
- `edited_delay_cuts_path`
- `pause_cuts_on_original_path`
- `output_mode`

### 输出

```json
{
  "final_video_path": "...",
  "final_video_url": "...",
  "groundtruth_url": "... or null",
  "groundtruth_tos_key": "... or null",
  "normalized_video_path": "... or null",
  "normalized_process_path": "... or null",
  "cut_plan_path": "...",
  "encoding_params": {
    "input_bitrate": 8000000,
    "output_bitrate": 8000000,
    "maxrate": 8000000,
    "bufsize": 16000000,
    "mode": "original"
  }
}
```

### 注意

- 如果 `vertical_1080p`，要先取 normalize 后视频的真实时长和码率信息
- cut plan 与最终视频都要保存
- `final_video.mp4` 上传 TOS 成功后，任务才能标记为 `success`
- GroundTruth 上传状态单独记录，不与最终视频上传状态共用

---

## 七、数据模型

建议任务表至少包含：

```sql
CREATE TABLE smart_cut_tasks (
    id UUID PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    status VARCHAR(32) NOT NULL,

    original_video_url TEXT NOT NULL,
    original_video_tos_key TEXT,
    reference_text_url TEXT NOT NULL,
    reference_text_tos_key TEXT,
    input_upload_status VARCHAR(32),

    analyze_script_url TEXT,
    analyze_audio_a_url TEXT,
    analyze_asr_result_url TEXT,
    analyze_delay_cuts_url TEXT,

    active_edited_script TEXT,
    active_edit_id UUID,
    active_delay_cuts_url TEXT,
    active_audio_a_url TEXT,
    active_pause_cuts_audio_a_url TEXT,
    active_pause_cuts_original_url TEXT,
    active_audio_b_url TEXT,

    final_output_mode VARCHAR(32),
    feed_to_ai BOOLEAN DEFAULT TRUE,
    finalize_source_edit_id UUID,
    final_video_url TEXT,
    final_video_tos_key TEXT,
    final_upload_status VARCHAR(32),
    normalized_video_url TEXT,
    normalized_process_url TEXT,
    final_cut_plan_url TEXT,
    groundtruth_url TEXT,
    groundtruth_tos_key TEXT,
    groundtruth_upload_status VARCHAR(32),

    work_dir TEXT,
    processing_params JSONB,
    input_media_info JSONB,
    error_stage VARCHAR(32),
    error_message TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);
```

如果需要保留多次试听历史，再单独加 `smart_cut_edits` 表。

如果新增 `smart_cut_edits`，建议至少包含：

```sql
CREATE TABLE smart_cut_edits (
    id UUID PRIMARY KEY,
    task_id UUID NOT NULL REFERENCES smart_cut_tasks(id),
    edited_script TEXT NOT NULL,
    delay_cuts_url TEXT,
    audio_a_url TEXT,
    pause_cuts_audio_a_url TEXT,
    pause_cuts_original_url TEXT,
    audio_b_url TEXT,
    audio_b_tos_key TEXT,
    status VARCHAR(32) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

并约束：

- `active_edit_id` 指向最后一次成功 preview 的 edit
- `finalize_source_edit_id` 记录最终视频实际基于哪一次成功 preview

---

## 八、前后端协议

## 8.1 脚本协议

- 后端存储：大括号格式纯文本
- 前端展示：`delete_ranges`
- 前端提交：大括号格式纯文本为主，`delete_ranges` 仅作辅助校验
- preview 阶段只允许修改删除标记，不允许修改正文字符内容

不把 HTML `<del>` 当协议。

## 8.2 上传协议

大文件采用“前端直传 TOS + 回写任务”的模式。

建议 API：

### 创建任务

```json
POST /api/smart-cut/tasks

response:
{
  "task_id": "uuid",
  "status": "created"
}
```

### 获取上传参数

```json
POST /api/smart-cut/tasks/{id}/upload-prepare

response:
{
  "video_upload": {...},
  "reference_upload": {...}
}
```

### 确认上传完成

```json
POST /api/smart-cut/tasks/{id}/upload-complete

{
  "original_video_url": "...",
  "original_video_tos_key": "...",
  "reference_text_url": "...",
  "reference_text_tos_key": "..."
}
```

只有 `upload-complete` 成功后，任务才能进入 `analyze`。

### upload-complete 安全校验

后端不能只信任前端传回的 URL，必须校验：

- 上传对象的 key 是否属于当前任务预分配的前缀
- URL/key 是否对应当前任务的上传凭证
- 对象是否真实存在于 TOS

不允许把任意外部 URL 直接绑定进任务。

## 8.3 finalize 请求协议

最终生成视频必须显式传输出规格：

```json
{
  "output_mode": "original",
  "feed_to_ai": true
}
```

或

```json
{
  "output_mode": "vertical_1080p",
  "feed_to_ai": true
}
```

不要在创建任务时就锁死 normalize 选择。

其中：

- `feed_to_ai` 对应前端复选框“投喂本文案给AI”
- 默认值为 `true`

## 8.4 成功结果协议

`GET /api/smart-cut/tasks/{id}` 在 `status=success` 时至少返回：

```json
{
  "status": "success",
  "final_video_url": "https://...",
  "download_text": "下载视频",
  "groundtruth_saved": true
}
```

前端直接把 `final_video_url` 渲染成下载超链接。

---

## 九、Worker 设计

Worker 仍放在 `website_aicut/worker/`，算法实现放在 `aicut2602/.../online_version/`。

### 队列任务

- `smart_cut_analyze`
- `smart_cut_preview`
- `smart_cut_finalize`

### 单任务工作目录

```text
/data/smart-cut/{task_id}/
├── input/
├── analyze/
├── preview/
└── final/
```

建议各阶段产物固定位置，避免猜路径。

### 文件流转规则

#### 输入文件

- 浏览器 -> TOS
- API 只记录 URL / key
- Worker -> 从 TOS 下载到本地工作目录

#### 输出文件

- `preview`:
  - Worker 本地生成 `audio_b.mp3`
  - Worker 上传到 TOS
  - API 返回 `audio_b_url`
  - 前端播放器使用该 URL 试听
- `finalize`:
  - Worker 本地生成 `final_video.mp4`
  - Worker 上传到 TOS
  - API 返回 `final_video_url`
  - 前端渲染下载链接
- `groundtruth`:
  - Worker 在 `finalize` 阶段按需生成 GroundTruth 目录
  - 上传到 TOS 指定目录路径
  - 回写 `groundtruth_url` / `groundtruth_tos_key`

### 建议失败状态

- `input_upload_failed`
- `preview_upload_failed`
- `final_upload_failed`
- `groundtruth_upload_failed`

避免“本地处理成功但 TOS 上传失败”被误标成成功。

---

## 十、实施顺序

### Phase 1

先做底层可跑通链路：

1. `pause_mapping.py`
2. `generate_audio_b.py`
3. `final_video_cutter.py`
4. `finalize_processor.py`

先解决最容易出事故的时间轴和 ffmpeg 参数问题。

### Phase 2

再做三阶段处理器：

1. `analyze_processor.py`
2. `preview_processor.py`
3. `finalize_processor.py`

### Phase 3

接 API 和 Worker：

1. 数据模型
2. 入队
3. 状态管理
4. 错误重试

### Phase 4

最后接前端页面和编辑器。

---

## 十一、验收标准

上线前至少验证以下场景：

1. `analyze` 正常产出脚本和 `audio_a`
2. 用户修改删除范围后，`preview` 能重算出新的 `audio_b`
3. `pause_cuts_on_original.json` 可被最终 cutter 正确读取
4. `original` 模式下最终视频剪点和试听一致
5. `vertical_1080p` 模式下：
   - 生成 `normalized_input.mp4`
   - 生成 `normalized_input.process.json`
   - 最终视频剪点不明显漂移
6. 输出码率真实符合 `min(input_bitrate, 12Mbps)`

如果第 5 条不成立，就不能把 normalize 放在 finalize，必须回退为 analyze 前置。

---

## 十二、最终结论

这版方案的核心落地方式是：

- 不碰原主流程的核心逻辑
- 但新增一个在线版封装层，补足：
  - Worker 三阶段
  - PauseCuts 映射
  - audio_b 试听
  - finalize 的 normalize 选择
  - 动态输出码率

其中最关键的三个实现点是：

1. `pause_cuts_on_original.json` 必须输出成 `DirectCutter` 兼容格式
2. 最终视频不能继续直接调用原 `DirectCutter.cut()`，而要通过在线版 cutter 注入动态码率
3. 所有路径必须使用容器内绝对路径，不能依赖当前工作目录
