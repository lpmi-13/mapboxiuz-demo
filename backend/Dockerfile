FROM python:3.12-slim

WORKDIR /app

# Install system deps (none needed beyond Python for this service)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
