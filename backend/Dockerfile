FROM python:3.11-slim

WORKDIR /app

# System deps for common wheels and runtime needs
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        openjdk-21-jdk \
        gradle \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

EXPOSE 3000

CMD ["python", "main.py"]
