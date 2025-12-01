FROM python:3.13.2-slim

WORKDIR /app


COPY requirements.txt .


RUN pip install --no-cache-dir --root-user-action=ignore -r requirements.txt


COPY . .

RUN mkdir -p /data/backups && \
    chmod 755 /data && \
    chmod 755 /data/backups


RUN chmod 755 /data

RUN echo "📁 Created /data directory for persistent storage"
RUN ls -la /

CMD ["python", "main.py"]
