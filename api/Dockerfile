FROM python:3.11-slim

WORKDIR /app

COPY api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r api/requirements.txt

COPY api/ .

EXPOSE 8080

CMD ["python", "main.py"]