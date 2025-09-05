FROM python:3.9

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV DOCKER_ENV=true

WORKDIR /app

# 复制requirements.txt并安装依赖
COPY requirements.txt .
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg supervisor && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir -r requirements.txt && \
    mkdir -p /var/log/supervisor

# 复制应用代码
COPY . .

# 复制supervisor配置
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# 创建必要的目录
RUN mkdir -p /app/downloads /app/data /app/cookies

# 设置权限
RUN chmod +x /app/start.sh

EXPOSE 8000 7860

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
