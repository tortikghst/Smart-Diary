FROM python:3.12-slim

# Установка системных зависимостей для библиотеки python-magic (libmagic1)
# А также шрифтов DejaVu для качественной генерации рассадки PNG в make_one
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /db_smart_dairy

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Экспонируем порт 8080, соответствующий базовому URL шлюза API из ТЗ
EXPOSE 8080

# Запуск uvicorn на порту 8080 с флагом --reload для оперативной отладки на хакатоне
CMD ["uvicorn", "scr.main:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]
