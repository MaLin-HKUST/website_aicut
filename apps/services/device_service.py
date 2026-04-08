"""Device Service - Worker 设备管理服务

提供设备注册、心跳更新、状态查询等功能。
"""

from datetime import datetime, timedelta
from typing import Optional, Any

from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from apps.models.device import SmartCutDevice, DeviceStatus


class DeviceService:
    """设备管理服务类
    
    封装所有与 SmartCutDevice 相关的业务逻辑。
    """
    
    def __init__(self, db: Session):
        """初始化服务
        
        Args:
            db: SQLAlchemy 数据库会话
        """
        self.db = db
    
    def register_device(
        self,
        worker_id: str,
        worker_name: str,
        supported_task_types: list[str],
        worker_version: Optional[str] = None,
        ip_address: Optional[str] = None,
        hostname: Optional[str] = None,
    ) -> SmartCutDevice:
        """注册或更新设备
        
        如果设备已存在，则更新其信息；否则创建新设备。
        注册时自动设置心跳时间为当前时间。
        
        Args:
            worker_id: Worker 唯一标识
            worker_name: Worker 显示名称
            supported_task_types: 支持的任务类型列表
            worker_version: Worker 版本号
            ip_address: IP 地址
            hostname: 主机名
            
        Returns:
            SmartCutDevice: 注册/更新后的设备对象
        """
        # 查询设备是否已存在
        stmt = select(SmartCutDevice).where(SmartCutDevice.worker_id == worker_id)
        device = self.db.execute(stmt).scalar_one_or_none()
        
        now = datetime.utcnow()
        
        if device is None:
            # 创建设备
            device = SmartCutDevice(
                worker_id=worker_id,
                worker_name=worker_name,
                status=DeviceStatus.IDLE,
                supported_task_types=supported_task_types,
                worker_version=worker_version,
                ip_address=ip_address,
                hostname=hostname,
                heartbeat_at=now,
                registered_at=now,
                updated_at=now,
            )
            self.db.add(device)
        else:
            # 更新设备信息
            device.worker_name = worker_name
            device.supported_task_types = supported_task_types
            device.worker_version = worker_version
            device.ip_address = ip_address
            device.hostname = hostname
            device.heartbeat_at = now
            device.updated_at = now
            # 如果之前是离线状态，恢复为空闲
            if device.status == DeviceStatus.OFFLINE:
                device.status = DeviceStatus.IDLE
        
        self.db.commit()
        self.db.refresh(device)
        return device
    
    def heartbeat(
        self,
        worker_id: str,
        status: Optional[DeviceStatus] = None,
        current_task_id: Optional[str] = None,
    ) -> Optional[SmartCutDevice]:
        """更新设备心跳
        
        Worker 定期调用此方法来报告自己仍然在线。
        可以顺便更新状态和当前任务。
        
        Args:
            worker_id: Worker 唯一标识
            status: 当前状态（可选，不更新则保持原值）
            current_task_id: 当前任务ID（可选）
            
        Returns:
            SmartCutDevice: 更新后的设备对象，设备不存在则返回 None
        """
        stmt = select(SmartCutDevice).where(SmartCutDevice.worker_id == worker_id)
        device = self.db.execute(stmt).scalar_one_or_none()
        
        if device is None:
            return None
        
        device.heartbeat_at = datetime.utcnow()
        device.updated_at = datetime.utcnow()
        
        # 如果之前是离线状态，恢复为空闲或指定状态
        if device.status == DeviceStatus.OFFLINE:
            device.status = status or DeviceStatus.IDLE
        elif status is not None:
            device.status = status
        
        # 更新当前任务
        if current_task_id is not None:
            device.current_task_id = current_task_id
        
        self.db.commit()
        self.db.refresh(device)
        return device
    
    def get_device(self, worker_id: str) -> Optional[SmartCutDevice]:
        """获取设备详情
        
        Args:
            worker_id: Worker 唯一标识
            
        Returns:
            SmartCutDevice: 设备对象，不存在则返回 None
        """
        stmt = select(SmartCutDevice).where(SmartCutDevice.worker_id == worker_id)
        return self.db.execute(stmt).scalar_one_or_none()
    
    def get_all_devices(self) -> list[SmartCutDevice]:
        """获取所有设备列表
        
        Returns:
            list[SmartCutDevice]: 所有设备列表
        """
        stmt = select(SmartCutDevice).order_by(SmartCutDevice.registered_at)
        return list(self.db.execute(stmt).scalars().all())
    
    def get_idle_workers(
        self,
        task_type: Optional[str] = None,
    ) -> list[SmartCutDevice]:
        """获取空闲的 Worker 列表
        
        查询状态为 idle 且在线的设备。如果指定了任务类型，
        还会检查设备是否支持该任务类型。
        
        Args:
            task_type: 任务类型（可选），如 "smart_cut_analyze"
            
        Returns:
            list[SmartCutDevice]: 符合条件的空闲设备列表
        """
        conditions = [SmartCutDevice.status == DeviceStatus.IDLE]
        
        # 只返回有心跳的设备（认为是在线的）
        # 实际离线检查由 check_offline_workers 处理
        conditions.append(SmartCutDevice.heartbeat_at.isnot(None))
        
        if task_type is not None:
            # JSON 字段查询 - SQLite 和 PostgreSQL 都支持
            conditions.append(
                SmartCutDevice.supported_task_types.contains([task_type])
            )
        
        stmt = (
            select(SmartCutDevice)
            .where(and_(*conditions))
            .order_by(SmartCutDevice.heartbeat_at.desc())  # 最近心跳的优先
        )
        return list(self.db.execute(stmt).scalars().all())
    
    def update_device_status(
        self,
        worker_id: str,
        status: DeviceStatus,
        current_task_id: Optional[str] = None,
    ) -> Optional[SmartCutDevice]:
        """更新设备状态
        
        Args:
            worker_id: Worker 唯一标识
            status: 新状态
            current_task_id: 当前任务ID（可选，用于关联任务）
            
        Returns:
            SmartCutDevice: 更新后的设备对象，设备不存在则返回 None
        """
        stmt = select(SmartCutDevice).where(SmartCutDevice.worker_id == worker_id)
        device = self.db.execute(stmt).scalar_one_or_none()
        
        if device is None:
            return None
        
        device.status = status
        device.updated_at = datetime.utcnow()
        
        if current_task_id is not None:
            device.current_task_id = current_task_id
        
        self.db.commit()
        self.db.refresh(device)
        return device
    
    def check_offline_workers(
        self,
        timeout_seconds: int = 60,
    ) -> list[SmartCutDevice]:
        """检查并标记超时未心跳的设备为离线
        
        查询心跳时间超过指定秒数的设备，将其状态标记为 offline。
        如果设备正在运行任务（running 状态），还会清空其 current_task_id。
        
        Args:
            timeout_seconds: 超时时间（秒），默认 60 秒
            
        Returns:
            list[SmartCutDevice]: 被标记为离线的设备列表
        """
        cutoff_time = datetime.utcnow() - timedelta(seconds=timeout_seconds)
        
        # 查询超时设备：心跳为 None 或心跳时间早于 cutoff_time
        stmt = select(SmartCutDevice).where(
            and_(
                SmartCutDevice.status != DeviceStatus.OFFLINE,
                SmartCutDevice.heartbeat_at.is_(None) | 
                (SmartCutDevice.heartbeat_at < cutoff_time)
            )
        )
        offline_devices = list(self.db.execute(stmt).scalars().all())
        
        for device in offline_devices:
            device.status = DeviceStatus.OFFLINE
            device.updated_at = datetime.utcnow()
            # 如果正在运行任务，释放任务关联
            if device.current_task_id is not None:
                device.current_task_id = None
        
        if offline_devices:
            self.db.commit()
            # 刷新所有对象
            for device in offline_devices:
                self.db.refresh(device)
        
        return offline_devices
    
    def unregister_device(self, worker_id: str) -> bool:
        """注销设备
        
        从数据库中删除设备记录。
        
        Args:
            worker_id: Worker 唯一标识
            
        Returns:
            bool: 是否成功删除
        """
        stmt = select(SmartCutDevice).where(SmartCutDevice.worker_id == worker_id)
        device = self.db.execute(stmt).scalar_one_or_none()
        
        if device is None:
            return False
        
        self.db.delete(device)
        self.db.commit()
        return True
