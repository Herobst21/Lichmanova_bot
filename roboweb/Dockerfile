FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn[standard] python-multipart requests
COPY app.py .
CMD ["uvicorn", "app:api", "--host", "0.0.0.0", "--port", "8000"]
