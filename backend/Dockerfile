FROM python:3.13-slim

WORKDIR /backend

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["python", "app.py"]
