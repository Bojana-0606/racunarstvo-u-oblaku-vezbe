FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ /app/
COPY data/ /app/data/
ENV PYTHONUNBUFFERED=1
CMD ["python", "/app/run_fold.py"]
