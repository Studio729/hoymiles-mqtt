# syntax=docker/dockerfile:1

FROM python:3.12-alpine

# Install system dependencies for health checks and database
RUN apk add --no-cache \
    curl \
    sqlite \
    libffi-dev \
    gcc \
    musl-dev \
    postgresql-dev \
    mariadb-dev \
    mariadb-connector-c \
    && rm -rf /var/cache/apk/*

WORKDIR /hoymiles-smiles

# Copy application files
COPY . .

# Install Python dependencies
RUN pip3 install --no-cache-dir -e .

# Create data directory
RUN mkdir -p /data /config

# Health check
# Note: Uses HEALTH_PORT environment variable, defaults to 8080
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${HEALTH_PORT:-8080}/ready || exit 1

# Expose health check port (default, can be changed via HEALTH_PORT env var)
EXPOSE 8080

# Run application
CMD [ "python3", "-m" , "hoymiles_smiles"]
