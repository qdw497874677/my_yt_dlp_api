FROM python:3.9

WORKDIR /app
COPY . .

RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg supervisor && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* &&\
    pip install --no-cache-dir -r requirements.txt && \
    mkdir -p /var/log/supervisor

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 8000 7860

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
