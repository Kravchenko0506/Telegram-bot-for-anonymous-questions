# Multi-stage build for smaller final image
FROM python:3.10-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 botuser

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=botuser:botuser . .

# Create data and logs directories
RUN mkdir -p data logs && chown -R botuser:botuser data logs

# Switch to non-root user
USER botuser

# Volume for database persistence
VOLUME ["/app/data", "/app/logs"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import asyncio; from models.database import check_db_connection; exit(0 if asyncio.run(check_db_connection()) else 1)"

# Run the bot
CMD ["python", "main.py"]