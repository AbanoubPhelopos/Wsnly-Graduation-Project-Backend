# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy project
COPY . /app/

# Expose port (adjust if needed)
EXPOSE 8000

# Run gunicorn (or manage.py runserver for dev)
# CMD ["gunicorn", "--bind", "0.0.0.0:8000", "Wslny.src.Presentation.wsgi:application"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
