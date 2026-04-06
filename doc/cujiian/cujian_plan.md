# 智能剪口播气口功能开发计划

## 项目概述
在现有视频处理平台中添加"智能剪口播气口"功能，实现人机协作的口播视频剪辑工具。

---

## 第一部分：生成 audio_b 的代码计划

### 1.1 需求分析

当前代码能力：
- ✅ Step A：生成 audio_a（剪掉口误、重复）
- ✅ Step B：检测停顿，生成 PauseCuts.json
- ❌ 缺失：根据 PauseCuts 从 audio_a 生成 audio_b

目标：补充 `generate_audio_b()` 函数，实现 audio_a → 停顿剪辑 → audio_b

### 1.2 技术方案

**方案：复用现有 FFmpeg 拼接逻辑**

参考 `script_to_delay_cuts.py` 中的 `generate_audio_a()` 方法，创建新的 `generate_audio_b()` 函数：

```python
def generate_audio_b(
    audio_a_path: str,          # 输入：Step A 生成的音频
    pause_cuts: List[Dict],     # 输入：停顿剪辑段列表
    output_path: str            # 输出：audio_b.mp3 路径
) -> Dict:
    """
    从 audio_a 中剪掉停顿部分，生成 audio_b
    
    逻辑：
    1. 获取 audio_a 时长
    2. 根据 pause_cuts 计算保留片段（invert_segments）
    3. 用 FFmpeg 提取保留片段
    4. 拼接生成 audio_b
    """
```

### 1.3 文件创建

| 文件路径 | 说明 |
|---------|------|
| `aicut2602/libs/cut_breakpoints/src/generate_audio_b.py` | 核心模块，实现 audio_b 生成逻辑 |

### 1.4 关键实现细节

**步骤 1：计算保留片段**
```python
def calculate_keep_segments_from_pauses(
    audio_duration: float,
    pause_cuts: List[Dict]
) -> List[Dict]:
    """根据停顿段计算需要保留的音频片段"""
    # 类似 calculate_keep_segments，但输入是 pause_cuts
```

**步骤 2：FFmpeg 音频拼接**
- 复用 `_extract_audio_segment()` 和 `_concat_audio_files()`
- 或者使用 filter_complex 一次性处理（更高效）

**步骤 3：时间轴映射**
- audio_b 的时间轴 = audio_a 时间轴 - 被剪掉的停顿时长
- 需要记录这个时间轴映射，供最终视频生成使用

### 1.5 接口设计

```python
# generate_audio_b.py

@dataclass
class AudioBResult:
    success: bool
    output_path: str
    keep_duration: float
    original_duration: float
    keep_ratio: float
    time_mapping: List[Dict]  # audio_a -> audio_b 时间映射

def generate_audio_b(
    audio_a_path: str,
    pause_cuts_path: str,      # PauseCuts.json 路径
    output_path: str
) -> AudioBResult:
    ...
```

---

## 第二部分：新功能开发计划

### 2.1 功能架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户交互流程                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Step A - 分析阶段                                               │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐ │
│  │ 上传视频    │───→│ 系统分析    │───→│ 展示带删除线的文案  │ │
│  │ + 文案      │    │ (ASR+AI)    │    │ (script_preview)    │ │
│  └─────────────┘    └─────────────┘    └─────────────────────┘ │
│                                                   │             │
│                                                   ▼             │
│  Step B - 试听阶段                                  │             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐ │
│  │ 用户编辑    │───→│ 生成试听    │───→│ 播放 audio_b        │ │
│  │ 删除线位置  │    │ (audio_b)   │    │                     │ │
│  └─────────────┘    └─────────────┘    └─────────────────────┘ │
│                                                   │             │
│                                                   ▼             │
│  最终输出                                          │             │
│  ┌──────────────────────────────────────────────┐ │             │
│  │ 用户确认 → 生成最终视频                      │◀┘             │
│  └──────────────────────────────────────────────┘               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 数据库设计

**新表：`smart_cut_tasks`**

```sql
CREATE TABLE smart_cut_tasks (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    
    -- 任务状态 (遵循 TASK_WORKFLOW.md)
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    -- draft, waiting_upload, processing_step_a, waiting_edit, 
    -- processing_step_b, waiting_confirm, processing_final, success, failed
    
    -- 输入文件
    video_file_id INTEGER REFERENCES task_files(id),
    reference_file_id INTEGER REFERENCES task_files(id),
    
    -- Step A 产物
    script_content TEXT,           -- AI 生成的 script（大括号格式）
    audio_a_url TEXT,              -- audio_a 文件链接
    delay_cuts JSONB,              -- DelayCutSegments 数据
    
    -- Step B 产物
    user_edited_script TEXT,       -- 用户编辑后的 script
    audio_b_url TEXT,              -- audio_b 文件链接
    pause_cuts JSONB,              -- PauseCuts 数据
    
    -- 最终产物
    final_video_url TEXT,          -- 最终视频链接
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    
    -- 错误信息
    error_message TEXT
);
```

**新表：`task_files`** (复用现有文件存储)
- 如果已有文件表则复用，否则创建

### 2.3 后端 API 设计

#### 2.3.1 创建任务
```http
POST /api/smart-cut/tasks
Request:
{
    "title": "任务名称"  // 可选
}
Response:
{
    "task_id": 123,
    "status": "draft",
    "upload_urls": {
        "video": { /* TOS 上传参数 */ },
        "reference": { /* TOS 上传参数 */ }
    }
}
```

#### 2.3.2 开始分析 (Step A)
```http
POST /api/smart-cut/tasks/{task_id}/analyze
Response:
{
    "task_id": 123,
    "status": "processing_step_a"
}
```

#### 2.3.3 获取分析结果
```http
GET /api/smart-cut/tasks/{task_id}
Response (Step A 完成后):
{
    "task_id": 123,
    "status": "waiting_edit",
    "script_content": "这是文案{要删除的部分}继续文案",
    "script_preview": "这是文案<del>要删除的部分</del>继续文案",  // 前端展示用
    "audio_a_url": "https://.../audio_a.mp3"
}
```

#### 2.3.4 提交编辑并生成试听 (Step B)
```http
POST /api/smart-cut/tasks/{task_id}/preview
Request:
{
    "edited_script": "这是文案<del>要删除的部分</del>继续文案"  // 删除线格式
}
Response:
{
    "task_id": 123,
    "status": "processing_step_b"
}
```

#### 2.3.5 获取试听结果
```http
GET /api/smart-cut/tasks/{task_id}
Response (Step B 完成后):
{
    "task_id": 123,
    "status": "waiting_confirm",
    "audio_b_url": "https://.../audio_b.mp3",
    "edited_script": "...",  // 用户编辑的内容
    "duration": 125.5  // audio_b 时长
}
```

#### 2.3.6 生成最终视频
```http
POST /api/smart-cut/tasks/{task_id}/finalize
Response:
{
    "task_id": 123,
    "status": "processing_final"
}
```

### 2.4 前端实现

#### 2.4.1 页面结构

```
apps/web/app/smart-cut/
├── page.tsx                    # 主页面
├── components/
│   ├── upload-section.tsx      # 视频+文案上传区域
│   ├── script-editor.tsx       # 带删除线的文本编辑器
│   ├── audio-player.tsx        # 音频播放器
│   └── status-bar.tsx          # 任务状态显示
├── hooks/
│   └── use-smart-cut.ts        # 任务状态管理
└── lib/
    └── script-formatter.ts     # 大括号 ↔ 删除线转换
```

#### 2.4.2 删除线文本编辑器

**交互设计：**
- 文本区域展示带删除线的内容
- 用户可选中文字，点击"删除"按钮添加删除线
- 点击已删除线的文字可取消删除
- 支持直接编辑文本内容

**技术实现：**
```typescript
// lib/script-formatter.ts

// 后端 → 前端：大括号转删除线
function bracketsToStrikethrough(text: string): string {
    return text.replace(/\{([^}]+)\}/g, '<del>$1</del>');
}

// 前端 → 后端：删除线转大括号
function strikethroughToBrackets(html: string): string {
    // 处理 <del> 标签
    return html.replace(/<del[^>]*>([^<]*)<\/del>/g, '{$1}');
}
```

#### 2.4.3 左侧导航更新

修改 `user-workspace-shell.tsx`：
```typescript
const primaryItems: NavItem[] = [
    { label: "文案生成语音", href: "/tts" },
    { label: "智能剪口播气口", href: "/smart-cut" },  // 新增
    { label: "视频剪辑", badge: "即将开放" },
    // ...
];
```

### 2.5 Worker 处理逻辑

**新任务类型：`smart_cut`**

Worker 处理流程：

```python
def process_smart_cut_task(task_id: str, input_dir: str, output_dir: str):
    """
    智能剪口播气口任务处理
    """
    # Step A: 生成 script 和 audio_a
    result_a = run_step_a(
        video_path=f"{input_dir}/video.mp4",
        reference_path=f"{input_dir}/reference.txt",
        output_dir=output_dir
    )
    # 产出: script.txt, audio_a.mp3, DelayCutSegments.json
    
    # 等待用户编辑（通过 API 轮询状态）
    wait_for_user_edit(task_id)
    
    # 获取用户编辑后的 script
    edited_script = fetch_user_edited_script(task_id)
    
    # Step B: 生成 audio_b
    result_b = run_step_b(
        audio_a_path=result_a['audio_a_path'],
        edited_script=edited_script,
        asr_result_path=result_a['asr_result_path'],
        output_dir=output_dir
    )
    # 产出: audio_b.mp3
    
    # 等待用户确认
    wait_for_user_confirm(task_id)
    
    # 生成最终视频
    final_video = generate_final_video(
        original_video=result_a['video_path'],
        edited_script=edited_script,
        output_dir=output_dir
    )
    
    return final_video
```

### 2.6 文件清单

#### 后端 (apps/api/)

| 文件 | 说明 |
|------|------|
| `app/models.py` | 添加 SmartCutTask 模型 |
| `app/schemas.py` | 添加 Pydantic schemas |
| `app/crud.py` | 添加 CRUD 操作 |
| `app/routers/smart_cut.py` | 新路由文件 |
| `app/main.py` | 注册新路由 |

#### 前端 (apps/web/)

| 文件 | 说明 |
|------|------|
| `app/smart-cut/page.tsx` | 主页面 |
| `app/smart-cut/components/*.tsx` | 组件 |
| `app/smart-cut/lib/script-formatter.ts` | 格式转换 |
| `components/user-workspace-shell.tsx` | 添加导航入口 |

#### 处理库 (aicut2602/)

| 文件 | 说明 |
|------|------|
| `libs/cut_breakpoints/src/generate_audio_b.py` | 生成 audio_b |
| `libs/cut_breakpoints/src/run_step_b.py` | Step B 流程封装 |

---

## 第三部分：实施步骤

### Phase 1: 核心功能开发 (3-4 天)

1. **Day 1**: 生成 audio_b 代码
   - 创建 `generate_audio_b.py`
   - 实现停顿剪辑 → audio_b 逻辑
   - 单元测试

2. **Day 2**: 后端 API
   - 数据库模型
   - Smart Cut API 路由
   - 与 TOS 文件上传集成

3. **Day 3**: 前端页面
   - Smart Cut 主页面
   - 上传组件
   - 删除线编辑器

4. **Day 4**: 集成测试
   - 前后端联调
   - 端到端流程测试

### Phase 2: Worker 集成 (2-3 天)

1. **Day 5**: Worker 任务处理
   - 添加 smart_cut 任务类型处理
   - Step A/B 流程封装
   - 状态更新机制

2. **Day 6-7**: 测试与优化
   - 完整流程测试
   - 错误处理
   - 性能优化

### Phase 3: UI 完善 (2 天)

1. **Day 8**: 交互优化
   - 加载状态
   - 错误提示
   - 进度展示

2. **Day 9**: 细节打磨
   - 音频播放器
   - 响应式布局
   - 边界情况处理

---

## 第四部分：风险与注意事项

### 4.1 技术风险

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| audio_b 时间轴映射复杂 | 中 | 复用现有 time_mapping.py 逻辑 |
| 大文件上传超时 | 中 | 使用分片上传或 TOS 直传 |
| 用户编辑 script 格式错误 | 低 | 前端验证 + 后端校验 |

### 4.2 依赖项

- 需要 `aicut2602` 库中的 `cut_breakpoints` 模块可用
- 需要 FFmpeg 安装在 worker 服务器
- 需要 TOS (对象存储) 配置正确

### 4.3 性能考虑

- Step A (ASR+AI) 可能耗时较长 (30s-2min)
- 需要在前端显示进度或 loading 状态
- Step B 生成 audio_b 相对快速 (< 10s)
- 最终视频生成可能耗时 (取决于视频长度)

---

## 附录：API 端点汇总

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/smart-cut/tasks | 创建任务 |
| GET | /api/smart-cut/tasks | 列表查询 |
| GET | /api/smart-cut/tasks/{id} | 获取详情 |
| POST | /api/smart-cut/tasks/{id}/analyze | 开始分析 |
| POST | /api/smart-cut/tasks/{id}/preview | 生成试听 |
| POST | /api/smart-cut/tasks/{id}/finalize | 生成视频 |
| DELETE | /api/smart-cut/tasks/{id} | 删除任务 |
