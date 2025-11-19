# 数据库Schema文档

## 概述

yt-dlp API 服务使用 SQLite 数据库来存储任务信息和状态。数据库文件默认位于 `./data/tasks.db`。

## 核心表结构

### tasks 表

存储所有任务（视频下载和字幕下载）的信息。

#### 当前Schema（版本 1.0）
```sql
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,                    -- 任务ID (UUID格式)
    url TEXT NOT NULL,                      -- 视频/媒体URL
    output_path TEXT NOT NULL,              -- 输出目录路径
    format TEXT NOT NULL,                   -- 格式（视频格式或字幕语言列表）
    status TEXT NOT NULL,                   -- 任务状态
    result TEXT,                            -- 任务结果（JSON格式）
    error_json TEXT,                        -- 错误信息（JSON格式）
    created_at TEXT NOT NULL,               -- 创建时间 (ISO 8601格式)
    updated_at TEXT NOT NULL                -- 更新时间 (ISO 8601格式)
);
```

#### 扩展Schema（版本 2.0 - 支持字幕功能）
```sql
-- 添加任务类型和字幕配置支持
ALTER TABLE tasks ADD COLUMN task_type TEXT DEFAULT 'video';
ALTER TABLE tasks ADD COLUMN subtitle_config TEXT;

-- 添加性能优化索引
CREATE INDEX idx_tasks_type ON tasks(task_type);
CREATE INDEX idx_tasks_type_status ON tasks(task_type, status);
CREATE INDEX idx_tasks_status_updated ON tasks(status, updated_at);
CREATE INDEX idx_tasks_type_status_created ON tasks(task_type, status, created_at DESC);
```

## 字段详细说明

### 基础字段

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | TEXT | PRIMARY KEY | UUID格式的任务唯一标识符 |
| url | TEXT | NOT NULL | YouTube视频URL或其他媒体URL |
| output_path | TEXT | NOT NULL | 下载文件的输出目录路径 |
| format | TEXT | NOT NULL | 视频格式或字幕语言列表（逗号分隔） |
| status | TEXT | NOT NULL | 任务状态，见下方状态说明 |
| result | TEXT | NULL | 任务执行结果（JSON格式存储） |
| error_json | TEXT | NULL | 错误信息（JSON格式存储） |
| created_at | TEXT | NOT NULL | 任务创建时间（ISO 8601格式） |
| updated_at | TEXT | NOT NULL | 任务最后更新时间（ISO 8601格式） |

### 新增字段（v2.0）

| 字段名 | 类型 | 约束 | 默认值 | 说明 |
|--------|------|------|--------|------|
| task_type | TEXT | | 'video' | 任务类型：'video' 或 'subtitle' |
| subtitle_config | TEXT | NULL | NULL | 字幕配置参数（JSON格式） |

## 任务状态说明

### status 字段值

| 状态值 | 说明 | 适用任务类型 |
|--------|------|-------------|
| pending | 任务已创建，等待处理 | 所有类型 |
| processing | 任务正在处理中 | 所有类型 |
| completed | 任务执行成功 | 所有类型 |
| failed | 任务执行失败 | 所有类型 |
| cancelled | 任务被取消 | 所有类型 |

### task_type 字段值

| 类型值 | 说明 | format字段含义 | result字段结构 |
|--------|------|---------------|---------------|
| video | 视频下载任务 | yt-dlp格式字符串（如"best", "mp4"） | 视频文件信息 |
| subtitle | 字幕下载任务 | 语言代码列表（如"en,zh"） | 字幕文件列表 |

## JSON字段结构

### result 字段结构

#### 视频任务 (task_type = 'video')
```json
{
    "output_file": "/downloads/video.mp4",
    "file_size": 52428800,
    "duration": 300.5,
    "format": "mp4",
    "resolution": "1920x1080",
    "fps": 30.0,
    "codec": "h264"
}
```

#### 字幕任务 (task_type = 'subtitle')
```json
{
    "downloaded_files": [
        {
            "language": "en",
            "path": "/downloads/video_en.srt",
            "format": "srt",
            "size": 24576,
            "is_auto_generated": false
        },
        {
            "language": "zh",
            "path": "/downloads/video_zh.vtt",
            "format": "vtt",
            "size": 18432,
            "is_auto_generated": true
        }
    ],
    "total_files": 2,
    "total_size": 43008
}
```

### subtitle_config 字段结构
```json
{
    "languages": ["en", "zh", "es"],
    "format": "srt",
    "auto_select": true,
    "prefer_manual": true,
    "cookie_path": "/cookies/cookies.txt",
    "output_naming": "title_language"
}
```

### error_json 字段结构
```json
{
    "error_code": "EXTRACTION_ERROR",
    "error_message": "Failed to extract video information",
    "error_type": "permanent_error",
    "timestamp": "2025-01-19T10:30:00Z",
    "retry_count": 3,
    "last_error": "HTTP 404: Video not found"
}
```

## 索引设计

### 基础索引
```sql
-- 主键索引（自动创建）
CREATE UNIQUE INDEX idx_tasks_id ON tasks(id);

-- 时间索引（用于任务清理）
CREATE INDEX idx_tasks_created_at ON tasks(created_at);
CREATE INDEX idx_tasks_updated_at ON tasks(updated_at);
```

### 查询优化索引
```sql
-- 状态查询优化
CREATE INDEX idx_tasks_status ON tasks(status);

-- 任务类型过滤
CREATE INDEX idx_tasks_type ON tasks(task_type);

-- 复合索引（常用查询组合）
CREATE INDEX idx_tasks_type_status ON tasks(task_type, status);
CREATE INDEX idx_tasks_status_updated ON tasks(status, updated_at);
CREATE INDEX idx_tasks_type_status_created ON tasks(task_type, status, created_at DESC);
```

### 性能分析
- `idx_tasks_type_status`: 优化按类型和状态查询任务
- `idx_tasks_status_updated`: 优化获取最近更新的任务
- `idx_tasks_type_status_created`: 优化任务列表分页查询

## 数据迁移

### 版本1.0到版本2.0迁移
```sql
-- 检查当前版本
PRAGMA user_version;

-- 添加新字段（向后兼容）
ALTER TABLE tasks ADD COLUMN task_type TEXT DEFAULT 'video';
ALTER TABLE tasks ADD COLUMN subtitle_config TEXT;

-- 更新数据库版本
PRAGMA user_version = 2;

-- 创建性能优化索引
CREATE INDEX idx_tasks_type ON tasks(task_type);
CREATE INDEX idx_tasks_type_status ON tasks(task_type, status);
CREATE INDEX idx_tasks_status_updated ON tasks(status, updated_at);
```

### 迁移脚本（Python）
```python
import sqlite3
import json
from datetime import datetime

def migrate_database_v1_to_v2(db_path: str):
    """将数据库从版本1.0迁移到2.0"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 检查当前版本
        cursor.execute("PRAGMA user_version")
        current_version = cursor.fetchone()[0]

        if current_version >= 2:
            print("数据库已经是最新版本")
            return

        print("开始数据库迁移...")

        # 添加新字段
        cursor.execute("ALTER TABLE tasks ADD COLUMN task_type TEXT DEFAULT 'video'")
        cursor.execute("ALTER TABLE tasks ADD COLUMN subtitle_config TEXT")

        # 创建索引
        cursor.execute("CREATE INDEX idx_tasks_type ON tasks(task_type)")
        cursor.execute("CREATE INDEX idx_tasks_type_status ON tasks(task_type, status)")
        cursor.execute("CREATE INDEX idx_tasks_status_updated ON tasks(status, updated_at)")

        # 更新版本号
        cursor.execute("PRAGMA user_version = 2")

        conn.commit()
        print("数据库迁移完成")

    except Exception as e:
        conn.rollback()
        print(f"迁移失败: {e}")
        raise
    finally:
        conn.close()

# 使用示例
migrate_database_v1_to_v2("./data/tasks.db")
```

## 查询示例

### 基础查询
```sql
-- 获取所有任务
SELECT * FROM tasks ORDER BY created_at DESC;

-- 获取特定任务
SELECT * FROM tasks WHERE id = 'task-id-here';

-- 获取正在处理的任务
SELECT * FROM tasks WHERE status = 'processing';
```

### 字幕任务查询
```sql
-- 获取所有字幕下载任务
SELECT * FROM tasks WHERE task_type = 'subtitle';

-- 获取已完成的字幕任务
SELECT id, url, created_at, result
FROM tasks
WHERE task_type = 'subtitle' AND status = 'completed'
ORDER BY updated_at DESC;

-- 获取失败的任务（最近24小时）
SELECT id, url, error_json, updated_at
FROM tasks
WHERE status = 'failed'
AND datetime(updated_at) > datetime('now', '-1 day')
ORDER BY updated_at DESC;
```

### 统计查询
```sql
-- 任务状态统计
SELECT
    task_type,
    status,
    COUNT(*) as count,
    AVG(
        CASE
            WHEN status = 'completed'
            THEN (julianday(updated_at) - julianday(created_at)) * 24 * 60
            ELSE NULL
        END
    ) as avg_duration_minutes
FROM tasks
GROUP BY task_type, status;

-- 每日任务统计
SELECT
    date(created_at) as date,
    task_type,
    COUNT(*) as total,
    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
FROM tasks
GROUP BY date(created_at), task_type
ORDER BY date DESC;
```

## 数据维护

### 清理旧数据
```sql
-- 删除30天前的已完成任务
DELETE FROM tasks
WHERE status = 'completed'
AND datetime(updated_at) < datetime('now', '-30 days');

-- 删除7天前的失败任务
DELETE FROM tasks
WHERE status = 'failed'
AND datetime(updated_at) < datetime('now', '-7 days');
```

### 数据库优化
```sql
-- 重建索引
REINDEX;

-- 分析表统计信息
ANALYZE;

-- 清理数据库碎片
VACUUM;
```

### 备份和恢复
```bash
# 备份数据库
sqlite3 ./data/tasks.db ".backup ./data/tasks_backup.db"

# 恢复数据库
cp ./data/tasks_backup.db ./data/tasks.db

# 导出SQL
sqlite3 ./data/tasks.db ".dump" > ./data/tasks_dump.sql

# 从SQL导入
sqlite3 ./data/tasks_new.db < ./data/tasks_dump.sql
```

## 性能优化建议

### 查询优化
1. **使用索引**: 确保WHERE条件使用索引字段
2. **限制结果**: 使用LIMIT进行分页查询
3. **避免SELECT ***: 只查询需要的字段
4. **批量操作**: 使用事务处理批量操作

### 存储优化
1. **定期清理**: 删除过期的完成任务
2. **JSON优化**: 考虑将复杂的JSON数据分离到专门的表
3. **文件路径**: 使用相对路径减少存储空间

### 并发处理
1. **连接池**: 使用连接池管理数据库连接
2. **事务隔离**: 设置合适的隔离级别
3. **锁机制**: 避免长时间锁住表

## 监控指标

### 数据库大小监控
```sql
-- 数据库大小
SELECT
    page_count * page_size as size_bytes,
    page_count * page_size / 1024.0 / 1024.0 as size_mb
FROM pragma_page_count(), pragma_page_size();
```

### 任务统计监控
```sql
-- 活跃任务数量
SELECT
    status,
    COUNT(*) as count
FROM tasks
WHERE status IN ('pending', 'processing')
GROUP BY status;

-- 任务完成率
SELECT
    COUNT(*) as total,
    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
    ROUND(
        SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) * 100.0 / COUNT(*),
        2
    ) as completion_rate
FROM tasks
WHERE created_at > datetime('now', '-24 hours');
```

## 故障排除

### 常见问题

**Q: 数据库文件锁定**
A: 确保没有其他进程在使用数据库，检查文件权限

**Q: 查询性能慢**
A: 检查是否使用了合适的索引，考虑ANALYZE更新统计信息

**Q: 数据库损坏**
A: 使用`.recover`命令尝试恢复，或从备份恢复

**Q: 磁盘空间不足**
A: 清理旧数据，考虑使用数据库压缩

### 诊断查询
```sql
-- 检查数据库完整性
PRAGMA integrity_check;

-- 检查外键约束
PRAGMA foreign_key_check;

-- 查看表结构
.schema tasks

-- 查看索引信息
PRAGMA index_list(tasks);

-- 查看统计信息
PRAGMA table_info(tasks);
```

---

*本文档最后更新时间: 2025-01-19*