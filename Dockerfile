FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY rivbot-discord.py .
COPY data/config.example.json /app/data/config.example.json

RUN mkdir -p /app/data && \
    if [ ! -f /app/data/config.json ]; then \
        cp /app/data/config.example.json /app/data/config.json; \
    fi


CMD ["python", "rivbot-discord.py"]
