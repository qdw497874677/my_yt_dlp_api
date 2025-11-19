## 1. 实现调度器基础设施
- [x] 1.1 添加 APScheduler 依赖到 requirements.txt
- [x] 1.2 在 main.py 中初始化调度器实例
- [x] 1.3 创建调度器启动和停止机制

## 2. 实现 yt-dlp 定时更新功能
- [x] 2.1 创建 yt-dlp 更新任务函数
- [x] 2.2 实现更新状态持久化存储
- [x] 2.3 添加更新失败重试机制

## 3. 实现配置管理
- [x] 3.1 创建配置数据结构（开关状态、更新频率等）
- [x] 3.2 实现配置的数据库存储
- [x] 3.3 添加默认配置（每天0点更新）

## 4. 添加 REST API 接口
- [x] 4.1 GET /scheduler/status - 获取调度器状态
- [x] 4.2 POST /scheduler/start - 启动调度器
- [x] 4.3 POST /scheduler/stop - 停止调度器
- [x] 4.4 GET /scheduler/config - 获取更新配置
- [x] 4.5 PUT /scheduler/config - 更新配置
- [x] 4.6 GET /scheduler/update-history - 获取更新历史

## 5. 集成测试和验证
- [x] 5.1 测试调度器启动和停止功能
- [x] 5.2 验证定时更新执行
- [x] 5.3 测试配置修改接口
- [x] 5.4 验证更新失败处理