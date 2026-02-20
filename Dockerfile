# Dockerfile for Anki Card Creator with Firefox/Scraping support
FROM python:3.11-slim-bookworm

# Install Firefox ESR and all dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    firefox-esr \
    wget \
    curl \
    ca-certificates \
    # X11 and display support
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrender1 \
    libxt6 \
    libxtst6 \
    # GTK and graphics
    libgtk-3-0 \
    libgdk-pixbuf2.0-0 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libatk1.0-0 \
    libcairo-gobject2 \
    libglib2.0-0 \
    # Font support
    fonts-noto-cjk \
    fonts-noto-color-emoji \
    # Utilities
    bzip2 \
    && rm -rf /var/lib/apt/lists/*

# Set display port to avoid crash
ENV DISPLAY=:99
ENV MOZ_HEADLESS=1

# Set working directory
WORKDIR /app

# Copy requirements first (for caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy geckodriver and extension from bin/ folder
COPY bin/geckodriver /usr/local/bin/geckodriver
RUN chmod +x /usr/local/bin/geckodriver

COPY bin/extension.xpi /app/extension.xpi

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Verify installation
RUN python3 -c "from src.services.scraping_service import scraping_service; print('Scraper module loads OK')"

# Expose port
EXPOSE 8000

# Run the application with startup script
CMD ["python3", "start.py"]
