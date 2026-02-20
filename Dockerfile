# Dockerfile for Anki Card Creator - Optimized for 512MB RAM
FROM python:3.11-slim-bookworm

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    ca-certificates \
    # Font support for Chinese
    fonts-noto-cjk \
    fonts-noto-color-emoji \
    # Playwright browser dependencies
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libdbus-1-3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (for caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers system-wide (before creating appuser)
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/playwright-browsers
RUN mkdir -p /opt/playwright-browsers && \
    python3 -m playwright install chromium --with-deps && \
    chmod -R 755 /opt/playwright-browsers

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Verify installation
RUN python3 -c "from src.services.scraping_service import scraping_service; print('Scraper module loads OK')"

# Expose port
EXPOSE 8000

# Run the application with startup script
CMD ["python3", "start.py"]
