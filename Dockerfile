FROM python:3.11-slim

WORKDIR /app

# Установка часового пояса внутри контейнера
RUN apt-get update && apt-get install -y tzdata && \
    ln -fs /usr/share/zoneinfo/Europe/Moscow /etc/localtime && \
    dpkg-reconfigure --frontend noninteractive tzdata

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN pip install aiohttp-socks

COPY bot.py .
COPY quizzes.json .

# Создаем папку для монтирования базы данных
RUN mkdir /app/data

CMD ["python", "bot.py"]
