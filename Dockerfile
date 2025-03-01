FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y supervisor && apt-get clean

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 50051 
EXPOSE 5000

CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]