# Используем Python 3.13 slim как базу
FROM python:3.13-slim

# Установка базовых инструментов для сборки и Rust
RUN apt-get update && \
    apt-get install -y build-essential curl git && \
    curl https://sh.rustup.rs -sSf | sh -s -- -y && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Добавляем Rust в PATH
ENV PATH="/root/.cargo/bin:$PATH"

# Создаем рабочую директорию
WORKDIR /app

# Копируем файлы проекта
COPY . /app

# Обновляем pip и устанавливаем зависимости
RUN python -m pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# Команда запуска бота
CMD ["python", "bot.py"]
