FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY scripts/server_upstream_timer.py /app/server_upstream_timer.py
USER 10001:10001
ENTRYPOINT ["python", "/app/server_upstream_timer.py"]
