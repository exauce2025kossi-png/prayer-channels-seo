FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y espeak-ng ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY mediaai-studio/requirements.txt /app/requirements.txt
COPY mediaai-studio/webapp/requirements.txt /app/requirements_web.txt
RUN pip install --no-cache-dir -r requirements.txt -r requirements_web.txt

COPY mediaai-studio/ /app/

EXPOSE 5000

CMD ["python", "webapp/app.py"]
