FROM python:3.11-slim

WORKDIR /app

RUN apt-get -o Acquire::Retries=3 update && apt-get -o Acquire::Retries=3 install -y --no-install-recommends \
    gcc default-libmysqlclient-dev pkg-config \
    fontconfig fonts-noto-cjk \
    ffmpeg \
    && fc-cache -f \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download rembg model (~176MB) so first API call isn't slow
RUN python -c "from rembg import new_session; new_session('u2net')" 2>&1 || true

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

COPY . .

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
