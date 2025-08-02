# Use Python 3.11 with Ubuntu as base
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DEBIAN_FRONTEND=noninteractive

# Set working directory
WORKDIR /app

# Install system dependencies including Chrome
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    gnupg \
    unzip \
    xvfb \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libwayland-client0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    libu2f-udev \
    libvulkan1 \
    && rm -rf /var/lib/apt/lists/*

# Add Google Chrome repository and install Chrome
RUN ARCH=$(dpkg --print-architecture) && \
    if [ "$ARCH" = "arm64" ]; then \
        # For ARM64, install chromium instead of Chrome
        apt-get update && \
        apt-get install -y chromium chromium-driver && \
        ln -s /usr/bin/chromium /usr/bin/google-chrome && \
        ln -s /usr/bin/chromedriver /usr/local/bin/chromedriver && \
        rm -rf /var/lib/apt/lists/*; \
    else \
        # For AMD64, use Google Chrome
        wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - && \
        echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list && \
        apt-get update && \
        apt-get install -y google-chrome-stable && \
        rm -rf /var/lib/apt/lists/*; \
    fi

# Install ChromeDriver (skip for ARM64 as we use chromium-driver)
RUN ARCH=$(dpkg --print-architecture) && \
    if [ "$ARCH" != "arm64" ]; then \
        CHROME_VERSION=$(google-chrome --version | grep -oE "[0-9]+\.[0-9]+\.[0-9]+") && \
        CHROMEDRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_VERSION%.*}") && \
        wget -O /tmp/chromedriver.zip "https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip" && \
        unzip /tmp/chromedriver.zip -d /tmp/ && \
        mv /tmp/chromedriver /usr/local/bin/chromedriver && \
        chmod +x /usr/local/bin/chromedriver && \
        rm /tmp/chromedriver.zip; \
    fi

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p downloaded_cvs logs sessions/browser_profiles config

# Copy configuration files if they don't exist
RUN if [ ! -f config/config.yaml ]; then \
        echo "Creating default config.yaml..."; \
        echo "search_criteria:" > config/config.yaml; \
        echo "  keywords:" >> config/config.yaml; \
        echo "    - \"Python developer\"" >> config/config.yaml; \
        echo "    - \"Software engineer\"" >> config/config.yaml; \
        echo "  locations:" >> config/config.yaml; \
        echo "    - \"London\"" >> config/config.yaml; \
        echo "    - \"Manchester\"" >> config/config.yaml; \
        echo "    - \"Birmingham\"" >> config/config.yaml; \
        echo "    - \"Edinburgh\"" >> config/config.yaml; \
        echo "    - \"Remote\"" >> config/config.yaml; \
        echo "  salary_range:" >> config/config.yaml; \
        echo "    min: 30000" >> config/config.yaml; \
        echo "    max: 80000" >> config/config.yaml; \
        echo "" >> config/config.yaml; \
        echo "download_settings:" >> config/config.yaml; \
        echo "  max_quantity: 10" >> config/config.yaml; \
        echo "  file_formats: [\"pdf\", \"doc\", \"docx\"]" >> config/config.yaml; \
        echo "  organize_by_keywords: true" >> config/config.yaml; \
        echo "  download_path: \"./downloaded_cvs/\"" >> config/config.yaml; \
        echo "" >> config/config.yaml; \
        echo "browser_settings:" >> config/config.yaml; \
        echo "  headless: true" >> config/config.yaml; \
        echo "  timeout: 30" >> config/config.yaml; \
        echo "  user_agent: \"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36\"" >> config/config.yaml; \
    fi

# Set execute permissions
RUN chmod +x main.py

# Create a startup script
RUN echo '#!/bin/bash' > start.sh && \
    echo 'set -e' >> start.sh && \
    echo '' >> start.sh && \
    echo 'echo "🚀 Starting CV-Library Scraper in Docker..."' >> start.sh && \
    echo 'echo "📋 Configuration:"' >> start.sh && \
    echo 'echo "   Chrome Version: $(google-chrome --version)"' >> start.sh && \
    echo 'echo "   ChromeDriver Version: $(chromedriver --version | head -1)"' >> start.sh && \
    echo 'echo "   Python Version: $(python --version)"' >> start.sh && \
    echo 'echo ""' >> start.sh && \
    echo '' >> start.sh && \
    echo '# Start Xvfb for headless Chrome (if needed)' >> start.sh && \
    echo 'if [ "${HEADLESS:-true}" = "false" ]; then' >> start.sh && \
    echo '    echo "📺 Starting virtual display..."' >> start.sh && \
    echo '    Xvfb :99 -screen 0 1920x1080x24 > /dev/null 2>&1 &' >> start.sh && \
    echo '    export DISPLAY=:99' >> start.sh && \
    echo 'fi' >> start.sh && \
    echo '' >> start.sh && \
    echo '# Run the scraper' >> start.sh && \
    echo 'echo "🔍 Starting CV scraper..."' >> start.sh && \
    echo 'python main.py "$@"' >> start.sh

RUN chmod +x start.sh

# Set the entrypoint
ENTRYPOINT ["./start.sh"]
CMD ["--keywords", "Python developer", "--quantity", "5", "--headless", "true"] 