#Sets the python image
FROM python:3.13-slim  


WORKDIR /app

#Copy and install dependencies
COPY backend/requirements.txt .
RUN pip install -r requirements.txt


COPY . .

#starts the application
CMD ["python", "-m", "backend.app"]
