FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY common/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY common/ ./common/
COPY worker/ ./worker/
RUN useradd -u 10001 -m appuser
USER 10001
CMD ["python", "worker/worker.py"]
