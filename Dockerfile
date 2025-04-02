# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# Use --no-cache-dir to reduce image size
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container at /app
# This includes app.py, ug_scraper.py, and the templates directory
COPY . .

# Make port 8080 available to the world outside this container
# Fly.io typically uses this port internally and maps external ports to it
EXPOSE 8080

# Define environment variable for Flask (optional but good practice)
ENV FLASK_APP=app.py

# Run app.py when the container launches using Gunicorn
# Bind to 0.0.0.0 to accept connections from outside the container
# Use a reasonable number of workers (e.g., based on CPU cores, often 2-4 for small apps)
# Fly.io will set the PORT environment variable, which Gunicorn uses by default if available,
# otherwise we default to 8080.
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
