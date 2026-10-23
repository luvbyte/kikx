FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    KIKX_VOLUMES=/data \
    KIKXFS=kikxfs

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY kikx/ /app/kikx/
COPY docker-entrypoint.py /app/kikx/docker_entrypoint.py

RUN mkdir -p /data

WORKDIR /app/kikx

EXPOSE 1303
VOLUME ["/data"]

ENTRYPOINT ["python", "docker_entrypoint.py"]
CMD ["python", "main.py"]
