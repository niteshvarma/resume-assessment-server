# Use a lightweight Python image
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Set non-root user for security
RUN useradd -m appuser

# Upgrade pip and install wheel to prefer prebuilt binaries
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Change ownership of the app directory to the non-root user
RUN chown -R appuser:appuser /app

# Switch to the non-root user
USER appuser

# Expose port 5000
#EXPOSE 5000
# Expose port 80
EXPOSE 80

# Set environment variables
ENV FLASK_APP=genfoundry.run
# Use production for deployment
ENV FLASK_ENV=production

# Run the Flask app using Gunicorn
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:80", "--timeout", "120", "genfoundry.run:app"]
