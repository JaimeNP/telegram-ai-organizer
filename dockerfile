FROM python:3.12-slim

WORKDIR /app

RUN pip install --upgrade pip
RUN pip install aiogram python-dotenv sqlalchemy asyncpg

COPY . /app

CMD ["python", "-m", "app.bot.main"]