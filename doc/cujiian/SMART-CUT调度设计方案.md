# SMART-CUT 调度系统设计方案

> 基于任务调度算法 v3 + 粗剪三阶段任务 (analyze/preview/finalize)
> 设计日期：2026-04-06

---

## 一、整体架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              用户浏览器                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│  │ 上传视频/文案 │→│ 调整删除范围 │→│ 试听 audio_b │→│ 选择规格+生成视频 │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↕ HTTP API
┌─────────────────────────────────────────────────────────────────────────┐
│                           A级主机 (调度中心)                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│  │  REST API   │  │  任务调度器  │  │  状态机引擎  │  │   TOS文件服务    │ │
│  │  - 创建任务  │  │  - FCFS队列 │  │  - 状态流转  │  │  - 上传/下载    │ │
│  │  - 查询状态  │  │  - 分配Worker│  │  - 异常处理  │  │  - 预签名URL   │ │
│  │  - 用户操作  │  │  - 心跳检测 │  │  - 超时清理  │  │                │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘ │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      数据库 (SQLite/PostgreSQL)                   │   │
│  │   smart_cut_tasks (任务表)  │  smart_cut_devices (设备表)         │   │
│  │   smart_cut_edits (编辑表)   │  alarm_logs (报警日志)             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↕ 任务队列 (Redis/RabbitMQ/DB轮询)
┌─────────────────────────────────────────────────────────────────────────┐
│                    SMART-CUT Worker 容器 (Docker)                        │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Entrypoint: smart-cut-entrypoint                                │   │
│  │  WorkDir: /data/smart-cut/{task_id}/                             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                     │
│  │ TaskPoller  │  │  analyze    │  │  preview    │  │   finalize      │ │
│  │  (任务轮询)  │→ │  (分析阶段) │→ │  (试听阶段) │→ │  (生成阶段)      │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘ │
│       ↑                                              ↓                  │
│  ┌─────────────┐                           ┌─────────────────┐         │
│  │ DeviceStatus│←─────────────────────────→│  TOS Upload     │         │
│  │  (设备表写入)│                           │  (结果上传)      │         │
│  └─────────────┘                           └─────────────────┘         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 二、数据模型设计

### 2.1 任务表 (smart_cut_tasks)

```sql
CREATE TABLE smart_cut_tasks (
    -- 主键与关联
    id UUID PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    user_id INTEGER NOT NULL,
    company VARCHAR(64) DEFAULT 'default',
    
    -- 任务类型与状态
    task_type VARCHAR(32) DEFAULT 'smart_cut',
    status VARCHAR(32) NOT NULL DEFAULT 'created',
    -- created -> analyze_pending -> analyze_running -> analyze_done
    -- -> preview_pending -> preview_running -> preview_done
    -- -> finalize_pending -> finalize_running -> success/failed
    
    -- 当前阶段信息
    current_stage VARCHAR(32) DEFAULT 'analyze',  -- analyze/preview/finalize
    current_step_index INTEGER DEFAULT 0,
    total_steps INTEGER DEFAULT 3,
    
    -- Worker分配
    assigned_worker_id VARCHAR(64),
    
    -- 输入文件 (TOS)
    original_video_url TEXT,
    original_video_tos_key TEXT,
    original_video_bitrate INTEGER,
    reference_text_url TEXT,
    reference_text_tos_key TEXT,
    input_upload_status VARCHAR(32) DEFAULT 'pending',
    
    -- Analyze 阶段产物
    analyze_script TEXT,           -- 大括号格式
    analyze_script_url TEXT,
    analyze_audio_a_url TEXT,      -- 内部使用，不对外
    analyze_asr_result_url TEXT,
    analyze_delay_cuts_url TEXT,
    analyze_status VARCHAR(32),
    analyze_started_at TIMESTAMP,
    analyze_completed_at TIMESTAMP,
    
    -- Preview 阶段产物 (当前生效的编辑)
    active_edit_id UUID,           -- 指向 smart_cut_edits
    active_edited_script TEXT,     -- 用户修改后的大括号格式
    active_delay_cuts_url TEXT,
    active_pause_cuts_original_url TEXT,  -- DirectCutter兼容格式
    active_audio_b_url TEXT,       -- 试听音频
    preview_status VARCHAR(32),
    preview_count INTEGER DEFAULT 0,  -- 预览次数统计
    
    -- Finalize 阶段配置与产物
    final_output_mode VARCHAR(32),  -- original / vertical_1080p
    feed_to_ai BOOLEAN DEFAULT TRUE, -- 是否投喂GroundTruth
    finalize_source_edit_id UUID,   -- 基于哪次preview
    
    final_video_url TEXT,
    final_video_tos_key TEXT,
    final_video_bitrate INTEGER,
    final_upload_status VARCHAR(32),
    
    normalized_video_url TEXT,      -- 1080P模式归一化视频
    normalized_process_url TEXT,    -- 归一化处理记录
    final_cut_plan_url TEXT,        -- 剪辑方案
    
    finalize_status VARCHAR(32),
    finalize_started_at TIMESTAMP,
    finalize_completed_at TIMESTAMP,
    
    -- GroundTruth
    groundtruth_url TEXT,
    groundtruth_tos_key TEXT,
    groundtruth_upload_status VARCHAR(32),
    
    -- 工作目录
    work_dir TEXT,                  -- /data/smart-cut/{task_id}/
    
    -- 处理参数与元数据
    processing_params JSON,         -- 各阶段参数记录
    input_media_info JSON,          -- 输入视频元信息
    output_media_info JSON,         -- 输出视频元信息
    
    -- 错误信息
    error_stage VARCHAR(32),
    error_message TEXT,
    error_detail TEXT,
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    keep_until TIMESTAMP,           -- 72小时保留期
    
    -- 索引
    INDEX idx_status (status),
    INDEX idx_user_id (user_id),
    INDEX idx_company (company),
    INDEX idx_assigned_worker (assigned_worker_id),
    INDEX idx_created_at (created_at)
);
```

### 2.2 编辑历史表 (smart_cut_edits)

```sql
CREATE TABLE smart_cut_edits (
    id UUID PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    task_id UUID NOT NULL REFERENCES smart_cut_tasks(id),
    
    edit_sequence INTEGER NOT NULL,  -- 第几次编辑
    
    -- 输入
    edited_script TEXT NOT NULL,     -- 用户修改后的大括号格式
    delete_ranges JSON,              -- 删除范围，用于前端展示
    
    -- 产物
    delay_cuts_url TEXT,
    audio_a_url TEXT,                -- 基于修改后的delay cuts生成
    pause_cuts_audio_a_url TEXT,
    pause_cuts_original_url TEXT,    -- DirectCutter格式
    audio_b_url TEXT,                -- 试听音频
    audio_b_tos_key TEXT,
    
    -- 状态
    status VARCHAR(32) NOT NULL DEFAULT 'running',
    -- running -> success/failed
    
    -- 元数据
    processing_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    
    -- 索引
    INDEX idx_task_id (task_id),
    INDEX idx_status (status)
);
```

### 2.3 设备表 (smart_cut_devices)

```sql
CREATE TABLE smart_cut_devices (
    worker_id VARCHAR(64) PRIMARY KEY,
    worker_name VARCHAR(128),
    
    -- 能力声明
    supported_task_types JSON NOT NULL,  -- ["smart_cut_analyze", "smart_cut_preview", "smart_cut_finalize"]
    max_concurrent_tasks INTEGER DEFAULT 1,
    
    -- 当前状态 (Worker写入)
    status VARCHAR(32) NOT NULL DEFAULT 'idle',
    -- idle / assign / running / post / error
    
    current_task_id UUID,
    current_task_stage VARCHAR(32),  -- analyze/preview/finalize
    current_task_progress INTEGER,   -- 0-100
    
    -- 心跳
    heartbeat_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 环境信息
    host_info JSON,                  -- IP、主机名、Docker容器ID等
    version VARCHAR(32),
    
    -- 索引
    INDEX idx_status (status),
    INDEX idx_heartbeat (heartbeat_at)
);
```

### 2.4 报警日志表 (alarm_logs)

```sql
CREATE TABLE alarm_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alarm_type VARCHAR(64) NOT NULL,   -- connection_error / business_error
    worker_id VARCHAR(64),
    task_id UUID,
    stage VARCHAR(32),
    current_status VARCHAR(32),
    description TEXT,
    details JSON,
    is_resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 三、A端（调度中心）设计

### 3.1 核心模块结构

```
website_aicut/apps/api/
├── models/
│   ├── __init__.py
│   ├── database.py          # SQLAlchemy 数据库连接
│   ├── task.py              # Task 模型
│   ├── edit.py              # Edit 模型
│   └── device.py            # Device 模型
├── services/
│   ├── __init__.py
│   ├── task_service.py      # 任务CRUD + 业务逻辑
│   ├── scheduler_service.py # 调度器核心
│   ├── state_machine.py     # 状态机引擎
│   ├── tos_service.py       # TOS文件服务
│   └── alarm_service.py     # 报警服务
├── routes/
│   ├── __init__.py
│   └── smart_cut.py         # REST API路由
└── scheduler/
    ├── __init__.py
    ├── main.py              # 调度器主进程
    └── worker_monitor.py    # Worker心跳监控
```

### 3.2 调度器核心逻辑 (SchedulerService)

```python
class SchedulerService:
    """
    调度器服务 - 负责任务调度、Worker分配、状态推进
    遵循原则：
    - 任务表由 A 写，Worker 只读
    - 设备表由 Worker 写，A 只读
    - FCFS + 能力匹配 + 空闲设备分配
    """
    
    def __init__(self, db: Session, poll_interval: int = 5):
        self.db = db
        self.poll_interval = poll_interval
        
    async def run_scheduler_loop(self):
        """主调度循环"""
        while True:
            try:
                # 1. 处理待调度任务
                await self.schedule_pending_tasks()
                
                # 2. 检查设备状态，推进任务状态
                await self.check_device_status_and_advance()
                
                # 3. 处理超时任务
                await self.handle_timeouts()
                
                # 4. 检查Worker心跳
                await self.check_worker_heartbeats()
                
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                
            await asyncio.sleep(self.poll_interval)
    
    async def schedule_pending_tasks(self):
        """
        FCFS调度：
        1. 扫描任务表中 pending 状态的任务
        2. 按创建顺序处理
        3. 查找 idle + 支持该任务类型的 Worker
        4. 分配任务
        """
        pending_tasks = self.db.query(Task).filter(
            Task.status.in_([
                'analyze_pending',
                'preview_pending', 
                'finalize_pending'
            ])
        ).order_by(Task.created_at).all()
        
        for task in pending_tasks:
            # 确定当前阶段需要的Worker类型
            stage = task.current_stage  # analyze/preview/finalize
            worker_type = f"smart_cut_{stage}"
            
            # 查找空闲Worker
            worker = self.db.query(Device).filter(
                Device.status == 'idle',
                Device.supported_task_types.contains(worker_type),
                Device.heartbeat_at > datetime.now() - timedelta(seconds=60)
            ).first()
            
            if worker:
                # 分配任务
                task.assigned_worker_id = worker.worker_id
                task.status = f"{stage}_assigned"
                
                # Worker状态由Worker自己更新，A端不直接写
                
                self.db.commit()
                logger.info(f"Task {task.id} assigned to {worker.worker_id} for {stage}")
    
    async def check_device_status_and_advance(self):
        """
        根据设备表观察结果，推进任务表状态：
        
        协作顺序：
        1. A 把任务改为 assigned
        2. Worker 看到任务属于自己，在设备表改为 assign
        3. Worker 启动后，在设备表改为 running
        4. A 读取到 running，把任务表改为 running
        5. Worker 完成后在设备表改为 post
        6. A 读取到 post，推进任务状态
        """
        # 查找 running 状态的 Worker
        running_workers = self.db.query(Device).filter(
            Device.status == 'running'
        ).all()
        
        for worker in running_workers:
            task = self.db.query(Task).filter(
                Task.id == worker.current_task_id
            ).first()
            
            if task and task.status.endswith('_assigned'):
                # Worker已经开始运行，更新任务状态
                task.status = task.status.replace('_assigned', '_running')
                task.updated_at = datetime.now()
                self.db.commit()
        
        # 查找 post 状态的 Worker
        post_workers = self.db.query(Device).filter(
            Device.status == 'post'
        ).all()
        
        for worker in post_workers:
            task = self.db.query(Task).filter(
                Task.id == worker.current_task_id
            ).first()
            
            if task and task.status.endswith('_running'):
                # Worker已完成当前阶段
                await self.handle_stage_completion(task, worker)
    
    async def handle_stage_completion(self, task: Task, worker: Device):
        """处理阶段完成"""
        stage = task.current_stage
        
        if stage == 'analyze':
            task.status = 'analyze_done'
            task.analyze_status = 'success'
            task.current_stage = 'preview'
            task.status = 'preview_pending'  # 等待用户操作
            task.analyze_completed_at = datetime.now()
            
        elif stage == 'preview':
            task.status = 'preview_done'
            task.preview_status = 'success'
            # preview 完成不自动进入 finalize，等待用户点击"生成视频"
            
        elif stage == 'finalize':
            task.status = 'success'
            task.finalize_status = 'success'
            task.completed_at = datetime.now()
            task.finalize_completed_at = datetime.now()
        
        # 释放Worker
        worker.status = 'idle'
        worker.current_task_id = None
        worker.current_task_stage = None
        
        self.db.commit()
    
    async def handle_timeouts(self):
        """处理超时任务"""
        # 72小时清理
        expired_tasks = self.db.query(Task).filter(
            Task.keep_until < datetime.now(),
            Task.status.notin_(['success', 'failed', 'abandoned'])
        ).all()
        
        for task in expired_tasks:
            task.status = 'timeout_closed'
            # TODO: 清理workspace
            
        self.db.commit()
```

### 3.3 REST API 设计

```python
# routes/smart_cut.py

@router.post("/tasks", response_model=TaskCreateResponse)
async def create_task(
    req: TaskCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建任务"""
    task = TaskService(db).create_task(
        user_id=current_user.id,
        company=current_user.company
    )
    return {"task_id": task.id, "status": task.status}

@router.post("/tasks/{task_id}/upload-prepare")
async def prepare_upload(
    task_id: UUID,
    db: Session = Depends(get_db)
):
    """获取TOS上传参数（预签名URL）"""
    upload_info = TOSService().generate_upload_urls(task_id)
    return upload_info

@router.post("/tasks/{task_id}/upload-complete")
async def confirm_upload(
    task_id: UUID,
    req: UploadCompleteRequest,
    db: Session = Depends(get_db)
):
    """确认上传完成，开始analyze"""
    # 安全校验：验证URL/key是否属于当前任务
    task = TaskService(db).confirm_upload(
        task_id=task_id,
        video_url=req.original_video_url,
        video_key=req.original_video_tos_key,
        text_url=req.reference_text_url,
        text_key=req.reference_text_tos_key
    )
    return {"status": task.status}

@router.get("/tasks/{task_id}", response_model=TaskDetailResponse)
async def get_task(
    task_id: UUID,
    db: Session = Depends(get_db)
):
    """获取任务详情"""
    return TaskService(db).get_task_detail(task_id)

@router.post("/tasks/{task_id}/preview")
async def create_preview(
    task_id: UUID,
    req: PreviewRequest,
    db: Session = Depends(get_db)
):
    """
    提交编辑后的脚本，生成preview
    前端传入：edited_script（大括号格式）
    """
    edit = TaskService(db).create_preview(
        task_id=task_id,
        edited_script=req.edited_script
    )
    return {"edit_id": edit.id, "status": edit.status}

@router.post("/tasks/{task_id}/finalize")
async def start_finalize(
    task_id: UUID,
    req: FinalizeRequest,
    db: Session = Depends(get_db)
):
    """
    开始生成最终视频
    需要传入：
    - output_mode: original / vertical_1080p
    - feed_to_ai: bool (默认true)
    - edit_id: 基于哪次preview（默认最后一次成功的）
    """
    task = TaskService(db).start_finalize(
        task_id=task_id,
        output_mode=req.output_mode,
        feed_to_ai=req.feed_to_ai,
        edit_id=req.edit_id
    )
    return {"status": task.status}

@router.post("/tasks/{task_id}/abandon")
async def abandon_task(
    task_id: UUID,
    db: Session = Depends(get_db)
):
    """用户放弃任务"""
    task = TaskService(db).abandon_task(task_id)
    return {"status": task.status}
```

---

## 四、Worker端设计

### 4.1 核心模块结构

```
website_aicut/worker/
├── __init__.py
├── main.py                      # Worker主进程入口
├── config.py                    # 配置管理
├── database.py                  # 数据库连接（只读任务表，写设备表）
├── poller.py                    # 任务轮询器
├── device.py                    # 设备状态管理
├── stages/
│   ├── __init__.py
│   ├── base.py                  # 阶段基类
│   ├── analyze.py               # analyze阶段处理器
│   ├── preview.py               # preview阶段处理器
│   └── finalize.py              # finalize阶段处理器
├── services/
│   ├── __init__.py
│   ├── file_store.py            # TOS文件下载/上传
│   ├── groundtruth.py           # GroundTruth记录
│   └── script_formatter.py      # 大括号↔删除线转换
└── processors/                  # 实际调用算法库
    ├── __init__.py
    ├── analyze_processor.py
    ├── preview_processor.py
    └── finalize_processor.py
```

### 4.2 Worker主流程

```python
# worker/main.py

class SmartCutWorker:
    """
    SMART-CUT Worker
    - 维护设备表（写入自己的状态）
    - 轮询任务表（只读，寻找分配给自己的任务）
    - 执行三阶段任务
    """
    
    def __init__(self, worker_id: str, worker_name: str):
        self.worker_id = worker_id
        self.worker_name = worker_name
        self.db = get_db_session()
        self.supported_stages = ['analyze', 'preview', 'finalize']
        
    async def run(self):
        """Worker主循环"""
        # 注册设备
        await self.register_device()
        
        while True:
            try:
                # 更新心跳
                await self.heartbeat()
                
                # 检查是否有分配给自己的任务
                task = self.find_assigned_task()
                
                if task:
                    # 执行任务
                    await self.execute_task(task)
                else:
                    # 空闲等待
                    await asyncio.sleep(5)
                    
            except Exception as e:
                logger.error(f"Worker error: {e}")
                await asyncio.sleep(10)
    
    def find_assigned_task(self) -> Optional[Task]:
        """查找分配给自己的任务"""
        return self.db.query(Task).filter(
            Task.assigned_worker_id == self.worker_id,
            Task.status.in_([
                'analyze_assigned',
                'preview_assigned',
                'finalize_assigned'
            ])
        ).first()
    
    async def execute_task(self, task: Task):
        """执行任务"""
        stage = task.current_stage
        
        # 更新设备状态为 assign
        await self.update_device_status('assign', task_id=task.id, stage=stage)
        
        try:
            # 创建阶段处理器
            processor = self.create_processor(stage, task)
            
            # 拉取输入文件
            await processor.prepare_input()
            
            # 更新设备状态为 running
            await self.update_device_status('running', task_id=task.id, stage=stage)
            
            # 执行阶段
            result = await processor.execute()
            
            # 上传产物
            await processor.upload_output(result)
            
            # 更新设备状态为 post
            await self.update_device_status('post', task_id=task.id, stage=stage)
            
        except Exception as e:
            logger.error(f"Task {task.id} stage {stage} failed: {e}")
            await self.update_device_status('error', error=str(e))
            raise
    
    def create_processor(self, stage: str, task: Task) -> BaseStageProcessor:
        """创建阶段处理器"""
        processors = {
            'analyze': AnalyzeProcessor,
            'preview': PreviewProcessor,
            'finalize': FinalizeProcessor
        }
        return processors[stage](task, self.db)
    
    async def update_device_status(self, status: str, **kwargs):
        """更新设备表（Worker只写自己的行）"""
        device = self.db.query(Device).filter(
            Device.worker_id == self.worker_id
        ).first()
        
        device.status = status
        device.heartbeat_at = datetime.now()
        
        if 'task_id' in kwargs:
            device.current_task_id = kwargs['task_id']
        if 'stage' in kwargs:
            device.current_task_stage = kwargs['stage']
        if 'error' in kwargs:
            device.error_message = kwargs['error']
        
        self.db.commit()
```

### 4.3 Analyze 阶段处理器

```python
# worker/stages/analyze.py

class AnalyzeProcessor(BaseStageProcessor):
    """
    Analyze阶段：
    1. 下载原视频和参考文案
    2. 调用 run_raw_cut.py --flow-a
    3. 解析产物，上传TOS
    4. 更新任务表（通过数据库）
    """
    
    async def execute(self) -> dict:
        work_dir = Path(self.task.work_dir) / 'analyze'
        work_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. 下载输入
        video_path = await self.download_input(
            self.task.original_video_url,
            work_dir / 'source_video.mp4'
        )
        text_path = await self.download_input(
            self.task.reference_text_url,
            work_dir / 'reference.txt'
        )
        
        # 2. 调用算法
        output_dir = work_dir / 'output'
        output_dir.mkdir(exist_ok=True)
        
        cmd = [
            'python', '/app/aicut2602/libs/cut_breakpoints/src/run_raw_cut.py',
            '-i', str(video_path),
            '-r', str(text_path),
            '-o', str(output_dir),
            '--flow-a',
            '-n', f'task_{self.task.id}'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise AnalyzeError(f"run_raw_cut failed: {result.stderr}")
        
        # 3. 解析产物
        prefix = f'task_{self.task.id}'
        
        script_file = output_dir / f'{prefix}_Script1.txt'
        asr_file = output_dir / f'{prefix}_ASR.Result.json'
        delay_cuts_file = output_dir / f'{prefix}_DelayCutSegments.json'
        audio_a_file = output_dir / f'{prefix}_audio_a.mp3'
        
        # 读取script（大括号格式）
        script = script_file.read_text(encoding='utf-8')
        
        # 4. 上传产物到TOS
        uploads = await asyncio.gather(
            self.upload_to_tos(script_file, f'smart-cut/{self.task.id}/analyze/script.txt'),
            self.upload_to_tos(asr_file, f'smart-cut/{self.task.id}/analyze/asr.json'),
            self.upload_to_tos(delay_cuts_file, f'smart-cut/{self.task.id}/analyze/delay_cuts.json'),
            self.upload_to_tos(audio_a_file, f'smart-cut/{self.task.id}/analyze/audio_a.mp3'),
        )
        
        return {
            'script': script,
            'script_url': uploads[0]['url'],
            'asr_url': uploads[1]['url'],
            'delay_cuts_url': uploads[2]['url'],
            'audio_a_url': uploads[3]['url'],
        }
```

### 4.4 Preview 阶段处理器

```python
# worker/stages/preview.py

class PreviewProcessor(BaseStageProcessor):
    """
    Preview阶段：
    1. 获取用户编辑后的script
    2. 重新生成delay cuts
    3. 检测pause cuts
    4. 生成audio_b（试听音频）
    5. 保存edit记录
    """
    
    async def execute(self) -> dict:
        work_dir = Path(self.task.work_dir) / 'preview'
        work_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. 获取edit记录
        edit = self.db.query(Edit).filter(
            Edit.id == self.task.active_edit_id
        ).first()
        
        # 2. 准备输入文件
        video_path = await self.download_input(
            self.task.original_video_url,
            work_dir / 'source_video.mp4'
        )
        asr_path = await self.download_input(
            self.task.analyze_asr_result_url,
            work_dir / 'asr.json'
        )
        
        # 3. 调用 preview_processor
        from online_version.src.preview_processor import PreviewProcessor as AlgoProcessor
        
        processor = AlgoProcessor(
            edited_script_path=work_dir / 'edited_script.txt',
            asr_result_path=asr_path,
            original_video_path=video_path,
            output_dir=work_dir / 'output',
            task_id=str(self.task.id)
        )
        
        # 写入edited_script
        (work_dir / 'edited_script.txt').write_text(edit.edited_script, encoding='utf-8')
        
        result = processor.process()
        
        # 4. 上传产物
        output_dir = work_dir / 'output'
        
        uploads = await asyncio.gather(
            self.upload_to_tos(
                output_dir / 'edited_delay_cuts.json',
                f'smart-cut/{self.task.id}/preview/{edit.id}/delay_cuts.json'
            ),
            self.upload_to_tos(
                output_dir / 'pause_cuts_on_original.json',
                f'smart-cut/{self.task.id}/preview/{edit.id}/pause_cuts.json'
            ),
            self.upload_to_tos(
                output_dir / 'audio_b.mp3',
                f'smart-cut/{self.task.id}/preview/{edit.id}/audio_b.mp3'
            ),
        )
        
        return {
            'edit_id': edit.id,
            'delay_cuts_url': uploads[0]['url'],
            'pause_cuts_original_url': uploads[1]['url'],
            'audio_b_url': uploads[2]['url'],
        }
```

### 4.5 Finalize 阶段处理器

```python
# worker/stages/finalize.py

class FinalizeProcessor(BaseStageProcessor):
    """
    Finalize阶段：
    1. 下载cuts配置
    2. 根据output_mode决定是否normalize
    3. 生成最终视频
    4. 上传到TOS
    5. 如果feed_to_ai，上传GroundTruth
    """
    
    async def execute(self) -> dict:
        work_dir = Path(self.task.work_dir) / 'finalize'
        work_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. 下载输入
        video_path = await self.download_input(
            self.task.original_video_url,
            work_dir / 'source_video.mp4'
        )
        
        # 2. 获取码率信息
        input_bitrate = await self.get_video_bitrate(video_path)
        output_bitrate = min(input_bitrate, 12_000_000) if input_bitrate else 12_000_000
        
        # 3. 处理normalize（如果需要）
        if self.task.final_output_mode == 'vertical_1080p':
            normalized_video = await self.normalize_video(video_path, work_dir)
            video_to_cut = normalized_video
        else:
            video_to_cut = video_path
        
        # 4. 下载cuts
        delay_cuts_path = await self.download_input(
            self.task.active_delay_cuts_url,
            work_dir / 'delay_cuts.json'
        )
        pause_cuts_path = await self.download_input(
            self.task.active_pause_cuts_original_url,
            work_dir / 'pause_cuts.json'
        )
        
        # 5. 生成最终视频
        from online_version.src.finalize_processor import FinalizeProcessor as AlgoProcessor
        
        processor = AlgoProcessor(
            video_source_path=video_to_cut,
            edited_delay_cuts_path=delay_cuts_path,
            pause_cuts_on_original_path=pause_cuts_path,
            output_mode=self.task.final_output_mode,
            output_bitrate=output_bitrate
        )
        
        final_video_path = work_dir / 'final_video.mp4'
        processor.process(str(final_video_path))
        
        # 6. 上传最终视频
        video_upload = await self.upload_to_tos(
            final_video_path,
            f'smart-cut/{self.task.id}/finalize/final_video.mp4'
        )
        
        # 7. 上传GroundTruth（如果需要）
        groundtruth_url = None
        if self.task.feed_to_ai:
            try:
                groundtruth_url = await self.upload_groundtruth(work_dir)
            except Exception as e:
                logger.error(f"GroundTruth upload failed: {e}")
                # 不阻塞主流程，只记录错误
        
        return {
            'final_video_url': video_upload['url'],
            'final_video_bitrate': output_bitrate,
            'groundtruth_url': groundtruth_url,
            'input_bitrate': input_bitrate,
        }
    
    async def normalize_video(self, video_path: Path, work_dir: Path) -> Path:
        """视频归一化"""
        from libs.cut_breakpoints.src.run_raw_cut import normalize_input_video
        
        output_path = work_dir / 'normalized_input.mp4'
        process_path = work_dir / 'normalized_input.process.json'
        
        normalize_input_video(
            input_path=str(video_path),
            output_path=str(output_path),
            process_path=str(process_path)
        )
        
        return output_path
    
    async def upload_groundtruth(self, work_dir: Path) -> str:
        """上传GroundTruth数据"""
        from worker.services.groundtruth import GroundTruthRecorder
        
        recorder = GroundTruthRecorder(
            company=self.task.company,
            task_id=str(self.task.id),
            work_dir=work_dir
        )
        
        # 收集数据
        data = {
            'reference_text': await self.download_text(self.task.reference_text_url),
            'original_video_url': self.task.original_video_url,
            'original_video_tos_key': self.task.original_video_tos_key,
            'asr_result': await self.download_json(self.task.analyze_asr_result_url),
            'analyze_script': self.task.analyze_script,
            'edited_script': self.task.active_edited_script,
        }
        
        # 生成并上传
        gt_dir = recorder.record(data)
        
        upload = await self.upload_to_tos(
            gt_dir / 'metadata.json',
            f'cujian_input_data/{self.task.company}/{datetime.now():%Y-%m}/cujian_userdata_{int(time.time())}/metadata.json'
        )
        
        return upload['url']
```

---

## 五、测试设计

### 5.1 测试策略

```
测试分层：
┌─────────────────────────────────────────┐
│  E2E测试 (tests/e2e/)                   │
│  - 完整用户流程测试                        │
│  - Docker Compose环境                     │
├─────────────────────────────────────────┤
│  集成测试 (tests/integration/)            │
│  - A端+Worker端到端                        │
│  - 数据库+TOS交互                          │
├─────────────────────────────────────────┤
│  单元测试 (worker/tests/, api/tests/)     │
│  - 各阶段处理器测试                        │
│  - 状态机测试                             │
│  - 工具函数测试                           │
└─────────────────────────────────────────┘
```

### 5.2 单元测试

```python
# worker/tests/test_analyze_processor.py

import pytest
from unittest.mock import Mock, patch, AsyncMock
from worker.stages.analyze import AnalyzeProcessor

class TestAnalyzeProcessor:
    """Analyze阶段单元测试"""
    
    @pytest.fixture
    def mock_task(self):
        task = Mock()
        task.id = "test-task-123"
        task.work_dir = "/tmp/test"
        task.original_video_url = "http://tos/video.mp4"
        task.reference_text_url = "http://tos/text.txt"
        return task
    
    @pytest.fixture
    def processor(self, mock_task):
        db = Mock()
        return AnalyzeProcessor(mock_task, db)
    
    @pytest.mark.asyncio
    async def test_execute_success(self, processor):
        """测试analyze成功流程"""
        # Mock下载
        processor.download_input = AsyncMock(return_value=Path("/tmp/video.mp4"))
        
        # Mock subprocess
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stderr="")
            
            # Mock文件读取
            with patch('pathlib.Path.read_text') as mock_read:
                mock_read.return_value = "今天天气{嗯}很好"
                
                # Mock上传
                processor.upload_to_tos = AsyncMock(return_value={'url': 'http://tos/result.txt'})
                
                result = await processor.execute()
        
        # 验证
        assert 'script' in result
        assert result['script'] == "今天天气{嗯}很好"
        processor.download_input.assert_called()
        processor.upload_to_tos.assert_called()
    
    @pytest.mark.asyncio
    async def test_execute_algorithm_failure(self, processor):
        """测试算法执行失败"""
        processor.download_input = AsyncMock(return_value=Path("/tmp/video.mp4"))
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=1, stderr="ASR failed")
            
            with pytest.raises(AnalyzeError):
                await processor.execute()
```

### 5.3 集成测试

```python
# tests/integration/test_full_flow.py

import pytest
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

class TestSmartCutFullFlow:
    """完整流程集成测试"""
    
    @pytest.fixture(scope='module')
    def db_engine(self):
        """测试数据库"""
        return create_engine('sqlite:///./test_smart_cut.db')
    
    @pytest.fixture
    def db_session(self, db_engine):
        Session = sessionmaker(bind=db_engine)
        session = Session()
        yield session
        session.rollback()
    
    @pytest.mark.asyncio
    async def test_analyze_to_finalize_flow(self, db_session):
        """
        测试完整流程：
        1. 创建任务
        2. 上传确认
        3. analyze
        4. preview
        5. finalize
        6. 验证结果
        """
        from apps.api.services.task_service import TaskService
        from apps.api.services.scheduler_service import SchedulerService
        from worker.main import SmartCutWorker
        
        # 1. 创建任务
        task_service = TaskService(db_session)
        task = task_service.create_task(user_id=1, company='test')
        
        # 2. 确认上传
        task = task_service.confirm_upload(
            task_id=task.id,
            video_url='http://fake-tos/video.mp4',
            video_key='videos/test.mp4',
            text_url='http://fake-tos/text.txt',
            text_key='texts/test.txt'
        )
        assert task.status == 'analyze_pending'
        
        # 3. 模拟调度器分配
        scheduler = SchedulerService(db_session)
        await scheduler.schedule_pending_tasks()
        
        task = db_session.query(Task).filter(Task.id == task.id).first()
        assert task.status == 'analyze_assigned'
        
        # 4. 模拟Worker执行analyze
        with patch('worker.stages.analyze.subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            worker = SmartCutWorker('test-worker-1', 'Test Worker')
            await worker.execute_task(task)
            
            task = db_session.query(Task).first()
            # Worker执行完成后状态应为post，调度器推进后变为analyze_done
            
        # 5. 调度器推进状态
        await scheduler.check_device_status_and_advance()
        
        task = db_session.query(Task).first()
        assert task.status == 'preview_pending'
        assert task.analyze_script is not None
```

### 5.4 E2E测试

```python
# tests/e2e/test_user_journey.py

import pytest
import requests
import time

class TestUserJourney:
    """用户旅程E2E测试"""
    
    BASE_URL = "http://localhost:8000/api"
    
    def test_complete_user_workflow(self):
        """
        完整用户工作流：
        1. 用户创建任务
        2. 上传视频和文案
        3. 查看analyze结果
        4. 调整删除范围
        5. 试听preview
        6. 生成视频
        7. 下载视频
        """
        # 1. 创建任务
        resp = requests.post(f"{self.BASE_URL}/smart-cut/tasks")
        assert resp.status_code == 200
        task_id = resp.json()['task_id']
        
        # 2. 获取上传参数
        resp = requests.post(f"{self.BASE_URL}/smart-cut/tasks/{task_id}/upload-prepare")
        assert resp.status_code == 200
        upload_urls = resp.json()
        
        # 3. 上传文件到TOS（这里用FakeTos模拟）
        # ...
        
        # 4. 确认上传完成
        resp = requests.post(
            f"{self.BASE_URL}/smart-cut/tasks/{task_id}/upload-complete",
            json={
                'original_video_url': 'http://fake-tos/video.mp4',
                'original_video_tos_key': 'videos/test.mp4',
                'reference_text_url': 'http://fake-tos/text.txt',
                'reference_text_tos_key': 'texts/test.txt'
            }
        )
        assert resp.status_code == 200
        
        # 5. 轮询等待analyze完成
        for _ in range(60):  # 最多等60秒
            resp = requests.get(f"{self.BASE_URL}/smart-cut/tasks/{task_id}")
            status = resp.json()['status']
            if status == 'preview_pending':
                break
            time.sleep(1)
        else:
            pytest.fail("Analyze timeout")
        
        # 6. 获取script并调整
        task_detail = resp.json()
        script = task_detail['analyze_script']
        # 模拟用户调整：删除第一个{}内的内容
        edited_script = script  # 假设前端调整后返回
        
        # 7. 提交preview
        resp = requests.post(
            f"{self.BASE_URL}/smart-cut/tasks/{task_id}/preview",
            json={'edited_script': edited_script}
        )
        assert resp.status_code == 200
        
        # 8. 轮询等待preview完成
        edit_id = resp.json()['edit_id']
        for _ in range(60):
            resp = requests.get(f"{self.BASE_URL}/smart-cut/tasks/{task_id}")
            if resp.json()['preview_status'] == 'success':
                break
            time.sleep(1)
        
        # 9. 试听audio_b（验证URL可访问）
        audio_b_url = resp.json()['active_audio_b_url']
        resp = requests.head(audio_b_url)
        assert resp.status_code == 200
        
        # 10. 生成最终视频
        resp = requests.post(
            f"{self.BASE_URL}/smart-cut/tasks/{task_id}/finalize",
            json={
                'output_mode': 'original',
                'feed_to_ai': True,
                'edit_id': edit_id
            }
        )
        assert resp.status_code == 200
        
        # 11. 轮询等待完成
        for _ in range(120):
            resp = requests.get(f"{self.BASE_URL}/smart-cut/tasks/{task_id}")
            if resp.json()['status'] == 'success':
                break
            time.sleep(1)
        
        # 12. 验证结果
        result = resp.json()
        assert result['final_video_url'] is not None
        assert result['groundtruth_saved'] is True
```

---

## 六、部署架构

```yaml
# docker-compose.yml

version: '3.8'

services:
  # A级主机 - API服务
  api:
    build: ./apps/api
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite:///./website_aicut.db
      - REDIS_URL=redis://redis:6379
      - TOS_ENDPOINT=http://tos:9000
    volumes:
      - ./website_aicut.db:/app/website_aicut.db
      - ./logs:/app/logs
    depends_on:
      - redis
      - tos

  # A级主机 - 调度器
  scheduler:
    build: ./apps/api
    command: python -m scheduler.main
    environment:
      - DATABASE_URL=sqlite:///./website_aicut.db
    volumes:
      - ./website_aicut.db:/app/website_aicut.db
    depends_on:
      - api

  # SMART-CUT Worker
  smart_cut_worker:
    image: website_aicut-smart_cut_worker:latest
    volumes:
      - ~/projects/aicut2602:/app/aicut2602
      - ~/projects/website_aicut:/app/website_aicut
      - ~/docker_hub/FakeTos:/app/website_aicut/tests/test_cujiian/fake_tos
      - smart_cut_data:/data/smart-cut
    environment:
      - WORKER_ID=smart_cut_worker_1
      - WORKER_NAME=Smart Cut Worker 1
      - DATABASE_URL=sqlite:///./website_aicut.db
      - STAGES=analyze,preview,finalize
    depends_on:
      - api

  # 模拟TOS
  tos:
    image: minio/minio
    command: server /data --console-address ":9001"
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - tos_data:/data

  # Redis（用于可选的消息队列）
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  smart_cut_data:
  tos_data:
  redis_data:
```

---

## 七、关键设计决策总结

| 决策点 | 方案 | 理由 |
|--------|------|------|
| **调度方式** | A端FCFS轮询+Worker轮询 | 符合v3调度算法，简单可靠，无复杂MQ依赖 |
| **任务表写入** | 仅A端写入 | 符合原则1：任务表由A写，Worker只读 |
| **设备表写入** | 仅Worker写入自己的行 | 符合原则2：设备表由Worker写，A只读 |
| **Worker并发** | 单Worker单任务 | 符合原则3，简化状态管理 |
| **文件存储** | TOS直传，API只存URL | 大文件不经过API，降低带宽压力 |
| **编辑历史** | 独立smart_cut_edits表 | 支持多次preview，可追溯 |
| **GroundTruth** | 异步上传，失败不阻塞 | 保证核心功能可用性 |
| **码率控制** | min(input_bitrate, 12Mbps) | 满足需求，不高于输入质量 |
| **Normalize** | 只在finalize且选1080P时执行 | 避免重复处理，节约资源 |

---

*本文档为完整设计方案，实现时可根据实际情况调整细节。*
