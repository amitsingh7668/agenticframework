FROM python:3.11-slim

WORKDIR /app

# Copy FastAPI admin API code
COPY . .

# Install dependencies
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

EXPOSE 9000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9000"]
