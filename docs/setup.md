# Setup Guide

This guide walks you through setting up GeoInsight for local development using Docker Compose.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (v20.10+)
- [Docker Compose](https://docs.docker.com/compose/install/) (v2.0+)
- [Node.js](https://nodejs.org/) (v22+ recommended)
- [npm](https://www.npmjs.com/)

---

## Initial Setup

### 1. Prepare the Web Client

```bash
# Copy environment configuration
cp web/.env.example web/.env
```

### 2. Build and Start Docker Containers

```bash
docker compose build
docker compose up
```

> **Note:** Ensure all containers start and stay running before continuing. Check the logs for any errors.

### 3. Initialize the Database

While the containers are running, open a **separate terminal** and run:

```bash
# Apply database migrations
docker compose run --rm django python manage.py migrate

# Create an admin user (you will be prompted for email and password)
docker compose run --rm -it django python manage.py createsuperuser

# Create OAuth client for authentication
docker compose run --rm django python manage.py makeclient
```

> **Note:** The `createsuperuser` command prompts you to create login credentials (email and password). Use these credentials to sign into both the Admin Panel and User Interface. If you forget your password, run `createsuperuser` again to create a new admin account.

> **Windows Users:** If the `createsuperuser` command hangs or doesn't show prompts, prefix the command with `winpty`:
> ```bash
> winpty docker compose run --rm -it django python manage.py createsuperuser
> ```

### 4. Load Sample Data (Optional)

The ingest command loads datasets, charts, and project configuration from an ingestion file:

```bash
docker compose run --rm django python manage.py ingest {JSON_FILE}
```

Available ingest options (paths relative to `sample_data/`):
- `multiframe_test.json`
- `boston_floods.json`
- `la_wildfires.json`
- `new_york_energy/data.json`

---

## Running the Application

### Start the Services

**Default (CPU-only):**
```bash
docker compose up
```

**With GPU acceleration (NVIDIA systems only):**
```bash
docker compose --profile gpu up --scale celery=0
```

> **Note:** GPU mode requires NVIDIA drivers and [nvidia-docker](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) runtime.

### Access Points

| Service | URL |
|---------|-----|
| User Interface | http://localhost:8080/ |
| Admin Panel | http://localhost:8000/admin/ |
| API Documentation | http://localhost:8000/api/docs/swagger/ |

Log in using the credentials you created with `createsuperuser`.

### Stop the Services

Press `Ctrl+C` in the terminal running `docker compose up`, or run:

```bash
docker compose stop
```

---

## Application Maintenance

When new package dependencies or database schema changes occur, update your development environment:

```bash
# Pull latest base images
docker compose pull

# Rebuild containers (no cache)
docker compose build --pull --no-cache

# Apply any new migrations
docker compose run --rm django python manage.py migrate
```

---

## Troubleshooting

### Container Build Failures

If you encounter build errors related to Python packages:

1. **Clear Docker build cache:**
   ```bash
   docker compose build --no-cache
   ```

2. **Prune unused Docker resources:**
   ```bash
   docker system prune -a
   ```

### Database Connection Issues

Ensure PostgreSQL is running and healthy:

```bash
docker compose ps
docker compose logs postgres
```

### Port Conflicts

If ports 8000, 8080, 5432, or 9000 are in use, modify the port mappings in `docker-compose.override.yml`.

### GPU Not Available

If you see an error like:
```
Error response from daemon: could not select device driver "nvidia" with capabilities: [[gpu]]
```

This means GPU mode was requested but NVIDIA drivers aren't available. Use the default CPU mode instead:
```bash
docker compose up
```

GPU acceleration is optional and only needed for accelerated inferencing.

### Windows-Specific Issues

**Interactive commands don't work or hang:**

On Windows (especially Git Bash/MINGW), interactive Docker commands like `createsuperuser` may hang or fail to display prompts. Prefix the command with `winpty`:

```bash
winpty docker compose run --rm -it django python manage.py createsuperuser
```

**"No such container" errors:**

If you see errors like `No such container: django` when trying to attach to a running container, use `docker compose run` instead:

```bash
docker compose run --rm -it django python manage.py <command>
```

This creates a new container instance rather than attaching to an existing one.
