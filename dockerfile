FROM python:3.13.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y jq && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x /app/entrypoint.sh

ENTRYPOINT [ "/app/entrypoint.sh" ]

CMD ["python", "/app/scripts/bot.py"]
