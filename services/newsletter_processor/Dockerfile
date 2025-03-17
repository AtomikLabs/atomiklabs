FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
COPY pip.conf /etc/pip.conf
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ .

CMD ["python", "newsletter_processor.py"] 