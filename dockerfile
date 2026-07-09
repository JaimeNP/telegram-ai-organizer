FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .

RUN pip install --upgrade pip && \
    pip install aiogram python-dotenv

COPY . .

CMD ["python", "app/bot/main.py"]