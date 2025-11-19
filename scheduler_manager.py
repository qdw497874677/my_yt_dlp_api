"""
yt-dlp 定时更新调度器管理模块
"""
import asyncio
import sqlite3
import subprocess
import sys
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
import yt_dlp

logger = logging.getLogger(__name__)

@dataclass
class SchedulerConfig:
    """调度器配置"""
    enabled: bool = False
    cron_expression: str = "0 0 * * *"  # 每天0点
    timezone: str = "UTC"
    max_retries: int = 3
    retry_delay: int = 300  # 5分钟

@dataclass
class UpdateRecord:
    """更新记录"""
    id: Optional[int] = None
    timestamp: Optional[datetime] = None
    old_version: Optional[str] = None
    new_version: Optional[str] = None
    status: str = "pending"  # pending, running, success, failed
    error_message: Optional[str] = None
    retry_count: int = 0

class YtDlpSchedulerManager:
    """yt-dlp 调度器管理器"""

    def __init__(self, db_path: str = "data/tasks.db"):
        self.db_path = db_path
        self.scheduler = None
        self.update_lock = asyncio.Lock()
        self._init_database()

    def _init_database(self):
        """初始化数据库表"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 创建调度器配置表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scheduler_config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)

            # 创建更新历史表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS update_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    old_version TEXT,
                    new_version TEXT,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0
                )
            """)

            # 插入默认配置
            default_config = SchedulerConfig()
            for key, value in asdict(default_config).items():
                cursor.execute("""
                    INSERT OR IGNORE INTO scheduler_config (key, value)
                    VALUES (?, ?)
                """, (key, str(value)))

            conn.commit()
            conn.close()
            logger.info("调度器数据库初始化完成")

        except Exception as e:
            logger.error(f"初始化调度器数据库失败: {e}")
            raise

    def get_config(self) -> SchedulerConfig:
        """获取调度器配置"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT key, value FROM scheduler_config")
            config_data = {}
            for key, value in cursor.fetchall():
                if key == "enabled":
                    config_data[key] = value.lower() == "true"
                elif key in ["max_retries", "retry_delay"]:
                    config_data[key] = int(value)
                else:
                    config_data[key] = value

            conn.close()
            return SchedulerConfig(**config_data)

        except Exception as e:
            logger.error(f"获取调度器配置失败: {e}")
            return SchedulerConfig()

    def update_config(self, config: SchedulerConfig) -> bool:
        """更新调度器配置"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            for key, value in asdict(config).items():
                cursor.execute("""
                    INSERT OR REPLACE INTO scheduler_config (key, value)
                    VALUES (?, ?)
                """, (key, str(value)))

            conn.commit()
            conn.close()
            logger.info(f"调度器配置已更新: {asdict(config)}")
            return True

        except Exception as e:
            logger.error(f"更新调度器配置失败: {e}")
            return False

    def add_update_record(self, record: UpdateRecord) -> int:
        """添加更新记录"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO update_history
                (timestamp, old_version, new_version, status, error_message, retry_count)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                datetime.now(timezone.utc),
                record.old_version,
                record.new_version,
                record.status,
                record.error_message,
                record.retry_count
            ))

            record_id = cursor.lastrowid
            conn.commit()
            conn.close()

            return record_id

        except Exception as e:
            logger.error(f"添加更新记录失败: {e}")
            return 0

    def get_update_history(self, limit: int = 50) -> List[UpdateRecord]:
        """获取更新历史"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, timestamp, old_version, new_version, status, error_message, retry_count
                FROM update_history
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))

            records = []
            for row in cursor.fetchall():
                records.append(UpdateRecord(
                    id=row[0],
                    timestamp=datetime.fromisoformat(row[1]) if row[1] else None,
                    old_version=row[2],
                    new_version=row[3],
                    status=row[4],
                    error_message=row[5],
                    retry_count=row[6]
                ))

            conn.close()
            return records

        except Exception as e:
            logger.error(f"获取更新历史失败: {e}")
            return []

    async def setup_scheduler(self):
        """设置调度器"""
        if self.scheduler is None:
            # 配置作业存储
            jobstores = {
                'default': SQLAlchemyJobStore(url=f'sqlite:///{self.db_path}')
            }

            # 配置执行器
            executors = {
                'default': AsyncIOExecutor()
            }

            # 创建调度器
            self.scheduler = AsyncIOScheduler(
                jobstores=jobstores,
                executors=executors,
                timezone='UTC'
            )

            # 添加更新任务
            self.scheduler.add_job(
                func=self._execute_ytdlp_update,
                trigger='cron',
                id='ytdlp_update_job',
                replace_existing=True,
                **self._parse_cron_expression(self.get_config().cron_expression)
            )

    def _parse_cron_expression(self, cron_expr: str) -> Dict[str, Any]:
        """解析 cron 表达式"""
        parts = cron_expr.split()
        if len(parts) != 5:
            # 默认每天0点
            return {'hour': 0, 'minute': 0}

        return {
            'minute': int(parts[0]),
            'hour': int(parts[1]),
            'day': int(parts[2]),
            'month': int(parts[3]),
            'day_of_week': int(parts[4])
        }

    async def start_scheduler(self) -> bool:
        """启动调度器"""
        try:
            if self.scheduler is None:
                await self.setup_scheduler()

            if not self.scheduler.running:
                self.scheduler.start()
                logger.info("调度器已启动")
                return True
            return False

        except Exception as e:
            logger.error(f"启动调度器失败: {e}")
            return False

    async def stop_scheduler(self) -> bool:
        """停止调度器"""
        try:
            if self.scheduler and self.scheduler.running:
                self.scheduler.shutdown(wait=True)
                logger.info("调度器已停止")
                return True
            return False

        except Exception as e:
            logger.error(f"停止调度器失败: {e}")
            return False

    def get_scheduler_status(self) -> Dict[str, Any]:
        """获取调度器状态"""
        config = self.get_config()
        status = {
            "running": self.scheduler.running if self.scheduler else False,
            "config": asdict(config),
            "next_run": None
        }

        if self.scheduler:
            job = self.scheduler.get_job('ytdlp_update_job')
            if job:
                status["next_run"] = job.next_run_time.isoformat() if job.next_run_time else None

        return status

    async def update_job_schedule(self, cron_expression: str):
        """更新作业调度"""
        try:
            if self.scheduler:
                self.scheduler.reschedule_job(
                    'ytdlp_update_job',
                    trigger='cron',
                    **self._parse_cron_expression(cron_expression)
                )
                logger.info(f"作业调度已更新: {cron_expression}")
                return True
            return False

        except Exception as e:
            logger.error(f"更新作业调度失败: {e}")
            return False

    async def _execute_ytdlp_update(self):
        """执行 yt-dlp 更新任务"""
        async with self.update_lock:
            try:
                config = self.get_config()
                if not config.enabled:
                    logger.info("自动更新已禁用，跳过更新")
                    return

                # 记录当前版本
                old_version = yt_dlp.version.__version__

                # 创建更新记录
                record = UpdateRecord(
                    old_version=old_version,
                    status="running"
                )
                record_id = self.add_update_record(record)

                logger.info(f"开始执行 yt-dlp 自动更新，当前版本: {old_version}")

                # 执行更新
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"],
                    capture_output=True,
                    text=True,
                    timeout=300
                )

                if result.returncode == 0:
                    # 更新成功，获取新版本
                    try:
                        # 重新导入获取新版本
                        import importlib
                        import yt_dlp as yt_dlp_new
                        importlib.reload(yt_dlp_new)
                        new_version = yt_dlp_new.version.__version__
                    except:
                        new_version = "unknown"

                    # 更新记录
                    self._update_record_status(record_id, "success", new_version=new_version)
                    logger.info(f"yt-dlp 自动更新成功: {old_version} -> {new_version}")

                else:
                    # 更新失败
                    error_msg = result.stderr if result.stderr else "未知错误"
                    self._update_record_status(record_id, "failed", error_message=error_msg)
                    logger.error(f"yt-dlp 自动更新失败: {error_msg}")

                    # 重试逻辑
                    if record.retry_count < config.max_retries:
                        logger.info(f"将在 {config.retry_delay} 秒后重试更新")
                        await asyncio.sleep(config.retry_delay)
                        await self._execute_ytdlp_update()

            except Exception as e:
                logger.error(f"执行 yt-dlp 更新时发生异常: {e}")
                if 'record_id' in locals():
                    self._update_record_status(record_id, "failed", error_message=str(e))

    def _update_record_status(self, record_id: int, status: str, **kwargs):
        """更新记录状态"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            set_clause = "status = ?"
            values = [status]

            if 'new_version' in kwargs:
                set_clause += ", new_version = ?"
                values.append(kwargs['new_version'])

            if 'error_message' in kwargs:
                set_clause += ", error_message = ?"
                values.append(kwargs['error_message'])

            if 'retry_count' in kwargs:
                set_clause += ", retry_count = ?"
                values.append(kwargs['retry_count'])
            else:
                set_clause += ", retry_count = retry_count + 1"

            values.append(record_id)

            cursor.execute(f"UPDATE update_history SET {set_clause} WHERE id = ?", values)
            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"更新记录状态失败: {e}")

# 全局调度器管理器实例
scheduler_manager = YtDlpSchedulerManager()