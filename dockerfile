FROM python:3.12-slim

WORKDIR /app

COPY . /app

RUN pip install --upgrade pip
RUN pip install aiogram python-dotenv sqlalchemy asyncpg

CMD ["python", "-m", "app.bot.main"]