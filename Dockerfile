# Use full Python image (has prebuilt libraries)
FROM python:3.11

# Set working directory
WORKDIR /app

# Create non-root user
RUN useradd -m -u 1000 judge

# Copy requirements first (better caching)
COPY requirements.txt .

# Upgrade pip and install dependencies
# Using --prefer-binary allows pip to use prebuilt wheels whenever possible
RUN pip install --upgrade pip \
    && pip install --no-cache-dir --prefer-binary -r requirements.txt

# Copy application files
COPY app.py .
COPY models.py .
COPY database.py .
COPY schemas.py .
COPY auth.py .
COPY config.py .
COPY celery_app.py .
COPY tasks.py .
COPY redis_client.py .
COPY azure_executor.py .

# Change ownership to non-root user
RUN chown -R judge:judge /app

# Switch to non-root user
USER judge

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Run application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]