# Use an official Python runtime as a parent image
FROM python:3

# Set the working directory in the container
WORKDIR /app


# Copy the Python dependencies file to the container
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container
COPY . /app/


# It's better to set environment variables like DATABASE_URL in the docker-compose file or through the Docker run command for security reasons.
ENV DATABASE_URL=mongodb://mongo:27017/