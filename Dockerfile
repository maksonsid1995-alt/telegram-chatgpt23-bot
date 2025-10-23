# Используем официальный образ Python 3.13
FROM python:3.13-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы проекта
COPY main.py .
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Экспортируем порт (Render будет использовать этот)
ENV PORT=10000

# Команда запуска
CMD ["python", "main.py"]
