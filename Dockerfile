FROM python:3.10-slim

# Устанавливаем ffmpeg и необходимые системные библиотеки
RUN apt-get update && apt-get install -y \
    ffmpeg \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Проверяем, что ffmpeg установился
RUN ffmpeg -version

WORKDIR /app

# Копируем requirements и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код бота
COPY . .

# Запускаем бота
CMD ["python", "bot.py"]