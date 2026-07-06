FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY apps/worker /app
RUN pip install --no-cache-dir uv && uv pip install --system -e /app

CMD ["python", "-m", "app.main"]
