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
    # Additional deps for Chromium
    libcurl4 \
    libxml2 \
    libxslt1.1 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (for caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers to a system-wide location
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/playwright-browsers
RUN mkdir -p /opt/playwright-browsers && \
    python3 -m playwright install chromium --with-deps && \
    chmod -R 755 /opt/playwright-browsers

# Create non-root user
RUN useradd -m -u 1000 appuser

# Copy application code
COPY . .
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Set the browsers path for appuser too
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/playwright-browsers

# Verify installation
RUN python3 -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); b = p.chromium.launch(); b.close(); print('Playwright OK')"

# Expose port
EXPOSE 8000

# Run the application with startup script
CMD ["python3", "start.py"]
