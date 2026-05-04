FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies
COPY besscom/backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app

ENV PORT=8001
EXPOSE 8001

CMD ["uvicorn", "besscom.backend.main:app", "--host", "0.0.0.0", "--port", "8001"]
