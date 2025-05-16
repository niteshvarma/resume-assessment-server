# Use a lightweight Python image
FROM python:3.11-slim

WORKDIR /app

# Add a shared location for nltk data
ENV NLTK_DATA=/app/nltk_data

# Set non-root user
RUN useradd -m appuser

# Upgrade pip and install wheel to prefer prebuilt binaries
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download NLTK data into a location available to both root and appuser
#RUN mkdir -p /app/nltk_data && \
#    python3 -m nltk.downloader -d /app/nltk_data stopwords
#COPY . .
# Create directory for NLTK data
RUN mkdir -p /app/nltk_data

# Copy your local files into the container
COPY . .

# Run the NLTK download using the Python script
RUN python3 download_nltk.py

# Set correct ownership
RUN chown -R appuser:appuser /app

# Switch to non-root
USER appuser

# Expose port
EXPOSE 80

ENV FLASK_APP=genfoundry.run
ENV FLASK_ENV=production
ENV TIKTOKEN_CACHE_DIR=/tmp/tiktoken_cache

#CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:80", "--timeout", "120", "genfoundry.run:app"]

# Run Flask and Celery in parallel
CMD ["sh", "-c", "gunicorn -w 4 -b 0.0.0.0:80 --timeout 120 genfoundry.run:app & celery -A genfoundry.celery_app.celery_app worker --loglevel=info"]

