# Use a lightweight Python base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Set the working directory
WORKDIR /app

# Install system dependencies if needed (none strictly required for core flux-titan)
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     gcc \
#     && rm -rf /var/lib/apt/lists/*

# Copy the project files
COPY . .

# Install the package
RUN pip install --no-cache-dir .

# Command to run the bot
# Running as a one-shot execution. If used in Docker Compose with a scheduler, 
# this will be the entry command.
CMD ["flux-titan"]
