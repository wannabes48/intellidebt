# 1. Use an official, lightweight Python runtime
FROM python:3.10-slim

# 2. Set environment variables for optimized Python behavior
# Prevents Python from writing .pyc files to disk
ENV PYTHONDONTWRITEBYTECODE=1
# Prevents Python from buffering stdout and stderr (makes logs appear instantly)
ENV PYTHONUNBUFFERED=1

# 3. Set the working directory inside the container
WORKDIR /app

# 4. Install system-level dependencies for PostgreSQL and Scikit-Learn
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 5. Copy the requirements file first (to leverage Docker layer caching)
COPY requirements.txt /app/

# 6. Install Python dependencies without storing the cache to save space
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# 7. Copy the rest of the Intellidebt application code
COPY . /app/

# 8. Expose the port that Gunicorn will listen on
EXPOSE 8000

# 9. Start the production server
# We strictly limit it to 1 worker to prevent Out-Of-Memory crashes with the ML model
CMD ["gunicorn", "intellidebt.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "1"]