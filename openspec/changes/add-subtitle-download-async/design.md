## Context

当前yt-dlp API已经有字幕下载功能，但是同步模式。用户需要异步字幕下载能力来处理大量字幕或长时间运行的任务。现有架构使用ThreadPoolExecutor进行异步任务处理，有完整的任务管理系统和SQLite数据库持久化。

## Goals / Non-Goals

**Goals:**
- 将现有字幕下载功能集成到异步任务系统
- 保持API设计和响应格式的一致性
- 最小化数据库schema变更
- 复用现有代码和错误处理模式

**Non-Goals:**
- 不创建专门的字幕文件管理系统
- 不实现复杂的字幕格式转换（初始版本）
- 不添加ZIP打包功能（违反简洁原则）
- 不创造新的API响应格式

## Decisions

### Decision 1: 最小化数据库变更
**选择**: 添加两个字段到现有tasks表：`task_type` 和 `subtitle_config`
**理由**: 避免复杂的表结构变更，保持向后兼容，最小化迁移风险
**替代方案**: 创建专门的字幕任务表（过度设计）

### Decision 2: 复用现有任务处理框架
**选择**: 扩展现有任务处理器支持字幕类型，而非创建独立处理系统
**理由**: 保持代码一致性，减少重复逻辑，降低维护成本
**替代方案**: 独立的字幕任务调度器（增加不必要的复杂性）

### Decision 3: 统一API响应格式
**选择**: 新字幕下载端点返回标准格式 `{"status": "success", "task_id": "xxx"}`
**理由**: 与现有 `/download` 端点保持一致，降低客户端集成成本
**替代方案**: 返回字幕特定的响应格式（破坏一致性）

### Decision 4: 复用现有字段设计
**选择**: 字幕任务使用现有的 `format` 字段存储语言列表，而非新增字段
**理由**: 避免数据模型膨胀，保持字段语义一致性
**替代方案**: 为字幕创建专门的字段（违反DRY原则）

## Technical Architecture

### Database Schema变更
```sql
-- 最小化变更，仅添加必要字段
ALTER TABLE tasks ADD COLUMN task_type TEXT DEFAULT 'video';
ALTER TABLE tasks ADD COLUMN subtitle_config TEXT;  -- JSON格式

-- 创建索引以提高查询性能
CREATE INDEX idx_tasks_type ON tasks(task_type);
CREATE INDEX idx_tasks_type_status ON tasks(task_type, status);
```

### API端点设计
```python
# 新增端点，遵循现有设计模式
POST /download-subtitles
{
    "url": "https://youtube.com/watch?v=xxx",
    "output_path": "./downloads",  # 可选，默认值
    "languages": ["en", "zh"],     # 语言列表
    "auto_select": true            # 自动选择最佳字幕
}

# 响应格式（与现有/download端点一致）
{
    "status": "success",
    "task_id": "uuid-string"
}
```

### Task模型扩展
```python
class Task(BaseModel):
    id: str
    url: str
    output_path: str
    format: str                      # 视频任务：格式；字幕任务：语言列表
    status: str
    task_type: str = "video"         # 新增：任务类型
    subtitle_config: Optional[Dict] = None  # 新增：字幕特定配置
    result: Optional[Dict] = None
    error: Optional[str] = None
    created_at: str
    updated_at: str
```

### 异步处理逻辑
```python
async def download_subtitle_async(task_id: str):
    """异步字幕下载处理"""
    task = state.get_task(task_id)
    config = json.loads(task.subtitle_config or '{}')

    try:
        # 复用现有字幕下载函数
        result = download_subtitle(
            url=task.url,
            output_path=task.output_path,
            languages=config.get('languages', ['en']),
            cookies=state.cookies
        )

        # 更新任务状态（复用现有逻辑）
        state.update_task_status(task_id, "completed", result)
    except Exception as e:
        # 复用现有错误处理
        state.update_task_status(task_id, "failed", error=str(e))
```

## File Organization

### 新增/修改文件
```
main.py                    # 添加字幕下载端点和任务处理逻辑
gradio_app.py             # 添加字幕下载界面（可选）
database/                 # 数据库迁移脚本
└── migrations/
    └── 001_add_subtitle_support.sql
```

### 代码复用策略
- **完全复用**: `download_subtitle()` 函数 (main.py:616-678)
- **完全复用**: `get_video_subtitles()` 函数 (main.py:579-614)
- **最小扩展**: Task 模型和 `add_task()` 方法
- **标准实现**: 错误处理和HTTP响应格式

## Risks / Trade-offs

### 技术风险
- **数据库迁移**: 添加字段需要停机时间（约1-2秒）
  - **缓解**: 使用ALTER TABLE DEFAULT值，现有数据自动兼容
- **任务类型混淆**: 可能创建task_type为空的任务
  - **缓解**: 设置默认值"video"，添加数据验证

### 设计权衡
- **简洁性 vs 功能性**: 选择简洁性，不添加复杂格式转换
- **一致性 vs 专用性**: 选择API一致性，而非字幕专用功能
- **复用性 vs 独立性**: 选择代码复用，而非独立系统

## Migration Plan

### Phase 1: 数据库准备
```sql
-- 执行数据库迁移（<5秒）
ALTER TABLE tasks ADD COLUMN task_type TEXT DEFAULT 'video';
ALTER TABLE tasks ADD COLUMN subtitle_config TEXT;
```

### Phase 2: 代码部署
1. 更新 Task 模型定义
2. 扩展 `add_task()` 方法
3. 添加 `/download-subtitles` 端点
4. 更新任务处理器支持字幕类型

### Phase 3: 测试验证
1. 验证现有视频下载功能正常
2. 测试新的字幕下载功能
3. 检查任务状态查询和文件下载
4. 确认Gradio界面集成

### Rollback Plan
- **数据库**: 如果出现问题，可以删除新字段回退
- **代码**: 新功能独立，不影响现有代码路径
- **API**: 新端点，不影响现有客户端

## Open Questions

1. **字幕语言代码标准化**: 是否需要验证和标准化ISO 639-1语言代码？
2. **文件命名规则**: 字幕文件是否需要特殊的命名约定？
3. **并发限制**: 字幕下载任务是否需要独立的并发控制？
4. **存储清理**: 字幕文件的清理策略是否与视频文件一致？

## Implementation Notes

### 关键代码位置
- **字幕下载函数**: `main.py:616-678` (可直接复用)
- **字幕信息获取**: `main.py:579-614` (可直接复用)
- **Task模型定义**: `main.py:91-99` (需要扩展)
- **任务管理**: `main.py:224-238` (需要修改add_task方法)

### 性能考虑
- 字幕下载通常比视频下载快，不需要特殊的超时处理
- 数据库查询添加task_type索引，不影响现有查询性能
- 文件存储复用现有目录结构，无需特殊处理

### 安全考虑
- 字幕文件同样需要安全的文件名生成
- 路径验证复用现有逻辑
- 不引入新的安全风险点