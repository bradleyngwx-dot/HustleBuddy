# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set environment variables to prevent Python from writing .pyc files
# and to ensure stdout/stderr are unbuffered
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the rest of the project files into the container
COPY . /app/
RUN python manage.py collectstatic --noinput

# Apply database migrations, then run the web server
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn hustlebuddy.wsgi:application --bind 0.0.0.0:${PORT:-8000}"]
