FROM python:3.11-slim
WORKDIR /app

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY frontend/dist ./frontend/dist/

ENV DATA_DIR=/data
EXPOSE 8000

CMD ["python", "backend/main.py"]
