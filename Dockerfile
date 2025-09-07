FROM python:3.9

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV DOCKER_ENV=true

WORKDIR /app

# 安装系统依赖
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
        apt-utils && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 升级pip
RUN pip install --upgrade pip

# 复制requirements.txt并安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 创建必要的目录
RUN mkdir -p /app/downloads /app/data /app/cookies

# 复制应用代码
COPY . .

# 设置权限
RUN chmod +x /app/start.sh

EXPOSE 8000 7860

# 启动FastAPI服务
CMD ["python", "main.py"]
