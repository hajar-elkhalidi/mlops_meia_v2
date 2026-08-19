FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

# System dependencies required by dbt
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN python -m pip install --upgrade pip \
    && pip install -r requirements.txt

COPY . .

RUN mkdir -p \
    /runtime/data \
    /runtime/mlflow \
    /runtime/mlartifacts \
    /runtime/dagster \
    /runtime/monitoring

EXPOSE 8000 5000 3000 8001

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
