# 性能和扩展性分析

## 性能目标

### 响应时间目标
- **API响应时间**: < 200ms (任务提交)
- **任务创建时间**: < 100ms
- **字幕提取时间**: 2-10秒 (取决于视频长度和网络)
- **文件下载时间**: < 1秒 (字幕文件通常很小)

### 吞吐量目标
- **并发字幕下载任务**: 10个
- **每分钟任务提交**: 60个
- **峰值QPS**: 5-10 (字幕下载端点)

### 资源使用目标
- **内存使用**: < 100MB per字幕任务
- **CPU使用**: < 50% (正常负载)
- **磁盘I/O**: < 10MB/s (字幕文件写入)
- **网络带宽**: < 1MB/s (字幕提取)

## 性能瓶颈分析

### 1. 网络I/O瓶颈
**问题**: yt-dlp需要访问YouTube服务器获取字幕信息
**影响**: 字幕提取的主要延迟来源
**解决方案**:
- 实现连接池复用
- 添加DNS缓存
- 使用HTTP Keep-Alive
- 设置合理的超时时间

```python
# yt-dlp网络优化配置
network_opts = {
    'socket_timeout': 30,
    'retries': 3,
    'no_check_certificate': False,  # 保持SSL验证
    'http_chunk_size': 8192,        # 适当的块大小
}
```

### 2. 磁盘I/O瓶颈
**问题**: 大量并发字幕文件写入可能导致磁盘竞争
**影响**: 文件写入延迟增加
**解决方案**:
- 异步文件写入
- 文件写入队列
- 磁盘空间监控
- 临时文件管理

```python
import aiofiles

async def async_subtitle_write(content: str, filepath: str):
    """异步文件写入"""
    async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
        await f.write(content)
```

### 3. 数据库性能
**问题**: 任务状态查询频率高
**影响**: 数据库连接池耗尽
**解决方案**:
- 添加复合索引
- 连接池优化
- 查询缓存
- 批量操作

```sql
-- 性能优化索引
CREATE INDEX idx_tasks_type_status_created ON tasks(task_type, status, created_at);
CREATE INDEX idx_tasks_status_updated ON tasks(status, updated_at);

-- 复合索引用于常见查询模式
CREATE INDEX idx_tasks_type_status_created_desc ON tasks(task_type, status, created_at DESC);
```

## 扩展性设计

### 1. 水平扩展支持

**无状态设计**
- 所有状态存储在数据库中
- API服务器可水平扩展
- 负载均衡友好

**任务队列设计**
```python
# 使用Redis作为任务队列（未来扩展）
import redis
from rq import Queue

# 任务队列配置
subtitle_queue = Queue('subtitle-downloads', connection=redis.Redis())

def enqueue_subtitle_download(task_data: Dict):
    """将字幕下载任务加入队列"""
    job = subtitle_queue.enqueue(
        'worker.process_subtitle_task',
        task_data,
        timeout=300  # 5分钟超时
    )
    return job.id
```

### 2. 缓存策略

**字幕信息缓存**
```python
from functools import lru_cache
import hashlib

@lru_cache(maxsize=1000)
def get_video_info_cached(url: str) -> Dict:
    """视频信息缓存"""
    cache_key = hashlib.md5(url.encode()).hexdigest()

    # 检查Redis缓存
    cached = redis_client.get(f"video_info:{cache_key}")
    if cached:
        return json.loads(cached)

    # 从YouTube获取信息
    info = get_video_info_from_youtube(url)

    # 缓存30分钟
    redis_client.setex(f"video_info:{cache_key}", 1800, json.dumps(info))
    return info
```

**任务状态缓存**
```python
# 任务状态短期缓存（减少数据库查询）
TASK_STATUS_CACHE_TTL = 60  # 60秒

def get_task_status_cached(task_id: str) -> Dict:
    """获取缓存的任务状态"""
    cached = redis_client.get(f"task_status:{task_id}")
    if cached:
        return json.loads(cached)

    # 从数据库获取
    task = state.get_task(task_id)
    redis_client.setex(f"task_status:{task_id}", TASK_STATUS_CACHE_TTL, json.dumps(task))
    return task
```

### 3. 资源限制和配额

**请求频率限制**
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/download-subtitles")
@limiter.limit("5/minute")  # 每分钟5个请求
async def api_download_subtitles(request: Request, ...):
    pass

@app.get("/task/{task_id}")
@limiter.limit("30/minute")  # 每分钟30个查询
async def get_task_status(request: Request, task_id: str):
    pass
```

**资源使用监控**
```python
import psutil
import asyncio

class ResourceMonitor:
    """系统资源监控"""

    @staticmethod
    async def check_system_resources():
        """检查系统资源使用情况"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory_percent = psutil.virtual_memory().percent
        disk_free = psutil.disk_usage('./downloads').free

        # 资源阈值检查
        if cpu_percent > 80:
            raise ResourceError(f"High CPU usage: {cpu_percent}%")

        if memory_percent > 80:
            raise ResourceError(f"High memory usage: {memory_percent}%")

        if disk_free < 1024 * 1024 * 1024:  # 1GB
            raise ResourceError(f"Low disk space: {disk_free // (1024**3)}GB")
```

## 监控和指标

### 1. 性能指标

**关键性能指标(KPI)**
```python
from prometheus_client import Counter, Histogram, Gauge

# 请求计数器
subtitle_requests = Counter('subtitle_requests_total',
                          'Total subtitle download requests',
                          ['status', 'language'])

# 响应时间直方图
subtitle_duration = Histogram('subtitle_download_duration_seconds',
                            'Subtitle download duration',
                            buckets=[1, 2, 5, 10, 30, 60, 300])

# 并发任务数
concurrent_subtitle_tasks = Gauge('concurrent_subtitle_tasks',
                                'Number of concurrent subtitle tasks')

# 系统资源指标
cpu_usage = Gauge('system_cpu_usage_percent', 'System CPU usage')
memory_usage = Gauge('system_memory_usage_percent', 'System memory usage')
```

### 2. 实时监控

**性能监控装饰器**
```python
import time
from functools import wraps

def monitor_performance(metric_name: str):
    """性能监控装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)
                status = "success"
                return result
            except Exception as e:
                status = "error"
                raise
            finally:
                duration = time.time() - start_time

                # 记录指标
                if metric_name == "subtitle_download":
                    subtitle_duration.observe(duration)
                    subtitle_requests.labels(status=status).inc()

        return wrapper
    return decorator
```

### 3. 健康检查

**服务健康状态**
```python
@app.get("/health")
async def health_check():
    """服务健康检查"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {}
    }

    try:
        # 检查数据库连接
        db_status = await check_database_health()
        health_status["checks"]["database"] = db_status

        # 检查磁盘空间
        disk_status = check_disk_health()
        health_status["checks"]["disk"] = disk_status

        # 检查系统资源
        resource_status = check_resource_health()
        health_status["checks"]["resources"] = resource_status

        # 检查外部依赖
        external_status = await check_external_dependencies()
        health_status["checks"]["external"] = external_status

        # 综合健康状态
        all_healthy = all(check["status"] == "healthy"
                         for check in health_status["checks"].values())
        health_status["status"] = "healthy" if all_healthy else "degraded"

        return health_status

    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }
```

## 未来扩展计划

### 短期扩展 (3-6个月)
1. **字幕格式转换**: 添加SRT↔VTT↔ASS转换
2. **字幕质量检测**: 机器学习模型评估字幕质量
3. **批量视频处理**: 支持播放列表字幕下载
4. **字幕编辑功能**: 基础的时间轴和文本编辑

### 中期扩展 (6-12个月)
1. **分布式任务处理**: Redis Queue + Celery
2. **字幕搜索引擎**: 全文搜索字幕内容
3. **字幕翻译集成**: 自动翻译API集成
4. **云端存储支持**: S3/Google Drive集成

### 长期扩展 (1年以上)
1. **微服务架构**: 拆分为独立的字幕处理服务
2. **实时字幕流**: WebSocket实时字幕推送
3. **AI字幕生成**: 语音识别生成字幕
4. **多平台支持**: 扩展到其他视频平台

## 容量规划

### 服务器规格建议
```yaml
# 最小配置 (小规模部署)
resources_minimal:
  cpu: "2 cores"
  memory: "4GB RAM"
  disk: "50GB SSD"
  network: "100Mbps"

# 推荐配置 (中等规模)
resources_recommended:
  cpu: "4 cores"
  memory: "8GB RAM"
  disk: "200GB SSD"
  network: "1Gbps"

# 高性能配置 (大规模)
resources_high_performance:
  cpu: "8 cores"
  memory: "16GB RAM"
  disk: "500GB SSD"
  network: "10Gbps"
```

### 数据库优化
```sql
-- 表分区策略（未来扩展）
CREATE TABLE tasks_partitioned (
    LIKE tasks INCLUDING ALL
) PARTITION BY RANGE (created_at);

-- 按月分区
CREATE TABLE tasks_2025_01 PARTITION OF tasks_partitioned
FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

-- 自动清理旧数据
DELETE FROM tasks
WHERE status = 'completed'
AND created_at < datetime('now', '-30 days');
```

这个性能和扩展性设计确保了字幕下载功能能够从小规模部署平滑扩展到大规模生产环境，同时保持良好的性能表现和用户体验。