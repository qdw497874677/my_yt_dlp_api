#!/bin/bash
# Docker启动测试脚本

echo "🐳 Docker Gradio启动测试"
echo "=========================="

# 检查Docker是否运行
if ! command -v docker &> /dev/null; then
    echo "❌ Docker未安装或未运行"
    exit 1
fi

echo "✅ Docker可用"

# 检查docker-compose
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ docker-compose未安装"
    exit 1
fi

echo "✅ docker-compose可用"

# 构建镜像
echo "🔨 构建Docker镜像..."
docker-compose build

if [ $? -ne 0 ]; then
    echo "❌ Docker镜像构建失败"
    exit 1
fi

echo "✅ Docker镜像构建成功"

# 启动容器
echo "🚀 启动Docker容器..."
docker-compose up -d

if [ $? -ne 0 ]; then
    echo "❌ Docker容器启动失败"
    exit 1
fi

echo "✅ Docker容器启动成功"

# 等待服务启动
echo "⏳ 等待服务启动（30秒）..."
sleep 30

# 检查supervisor进程状态
echo "📊 检查supervisor进程状态..."
docker-compose exec yt-dlp-api-service supervisorctl status

# 检查端口是否可访问
echo "🔍 检查服务端口..."

# 检查FastAPI端口8000
echo "检查FastAPI (8000):"
if curl -f http://localhost:18000/docs &> /dev/null; then
    echo "✅ FastAPI服务正常 (http://localhost:18000)"
else
    echo "❌ FastAPI服务异常"
fi

# 检查Gradio端口7860
echo "检查Gradio (7860):"
if curl -f http://localhost:17860 &> /dev/null; then
    echo "✅ Gradio服务正常 (http://localhost:17860)"
else
    echo "❌ Gradio服务异常"
fi

# 显示最近的日志
echo "📋 显示最近的日志..."
echo "=== FastAPI 日志 ==="
docker-compose logs --tail=10 yt-dlp-api-service | grep -E "(fastapi|8000)" || echo "无FastAPI相关日志"

echo "=== Gradio 日志 ==="
docker-compose logs --tail=10 yt-dlp-api-service | grep -E "(gradio|7860)" || echo "无Gradio相关日志"

echo "=== Supervisor 日志 ==="
docker-compose logs --tail=20 yt-dlp-api-service | grep -E "(supervisor|STARTED|ENTERED|FATAL)"

echo ""
echo "🔧 调试命令："
echo "  查看完整日志: docker-compose logs -f yt-dlp-api-service"
echo "  查看进程状态: docker-compose exec yt-dlp-api-service supervisorctl status"
echo "  重启Gradio: docker-compose exec yt-dlp-api-service supervisorctl restart gradio"
echo "  进入容器: docker-compose exec yt-dlp-api-service bash"