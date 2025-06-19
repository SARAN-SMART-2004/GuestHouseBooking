# Dockerfile
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

COPY . /app/

RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose port 8000 (default for Gunicorn)
EXPOSE 8000

# Set environment variables for Django
ENV DJANGO_SETTINGS_MODULE=gbooking.settings

# Start Gunicorn
CMD ["gunicorn", "gbooking.wsgi:application", "--bind", "0.0.0.0:8000"]
