# Child Safety Location Monitoring System

A software project for monitoring children's locations and supporting guardian oversight through location tracking and safety-related features.

## Tech Stack

- **Backend:** Python, Flask
- **Database:** PostgreSQL
- **Containerization:** Docker, Docker Compose

## Prerequisites

Install the following before running the project:

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- Git

## Project Setup

### 1. Clone the Repository

```bash
git clone https://github.com/RalphD4/Scatela
cd Scatela
```

### 2. Configure Environment Variables

Create a `.env` file in the project root. 

```dotenv
POSTGRES_DB: scatela_db
POSTGRES_USER: scatela_user
POSTGRES_PASSWORD: change_me
```


### 3. Build and Start the Containers

From the project root, run:

```bash
docker compose up --build -d
```

This builds the backend image and starts the configured services in the background.

### 4. Verify the Containers

Check the status of the services:

```bash
docker compose ps
```

View backend logs:

```bash
docker compose logs api
```

View PostgreSQL logs:

```bash
docker compose logs postgres
```

### 5. Access the Application

If the Flask service publishes port `5001`, open:

http://localhost:5001/

### 6. Stop the Application

Stop and remove the Compose-managed containers and network:

```bash
docker compose down
```

The named PostgreSQL volume is retained by default, preserving database data between runs.

## Database

The project uses PostgreSQL for persistent data storage. The database service runs in a Docker container, with host port `5433` mapped to container port `5432`.

The `database/` directory contains the SQL schema definition.

## Development

Rebuild and restart services after changes to the backend code or dependencies:

```bash
docker compose up --build -d
```


