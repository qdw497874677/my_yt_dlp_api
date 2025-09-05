#!/bin/bash

# 启动脚本 - 同时启动FastAPI和Gradio服务

echo "正在启动 yt-dlp API 服务..."

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "错误: Docker未安装，请先安装Docker"
    exit 1
fi

# 检查Docker Compose是否安装
if ! command -v docker-compose &> /dev/null; then
    echo "错误: Docker Compose未安装，请先安装Docker Compose"
    echo "提示: 在较新的Docker版本中，可以使用 'docker compose' 命令"
    # 检查是否有docker compose（不带连字符的版本）
    if command -v docker &> /dev/null; then
        if docker compose version &> /dev/null; then
            echo "检测到 'docker compose' 命令，将使用该命令启动服务"
            DOCKER_COMPOSE_CMD="docker compose"
        else
            exit 1
        fi
    else
        exit 1
    fi
else
    DOCKER_COMPOSE_CMD="docker-compose"
fi

# 创建必要的目录
echo "创建必要的目录..."
mkdir -p downloads data cookies

# 启动服务
echo "启动服务中..."
echo "FastAPI服务将在 http://localhost:18000 启动"
echo "Gradio界面将在 http://localhost:17860 启动"
echo "按 Ctrl+C 停止服务"

# 使用检测到的命令启动服务
$DOCKER_COMPOSE_CMD up
