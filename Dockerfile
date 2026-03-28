# Stage 1: Build frontend
FROM node:20-alpine AS frontend-build
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --ignore-scripts || npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Production image
FROM python:3.12-slim
WORKDIR /app

# Install system deps for Pillow and bcrypt
RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg62-turbo-dev libffi-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./

# Copy built frontend
COPY --from=frontend-build /build/dist ./frontend/dist

# Create data directory (overridden by volume mount)
RUN mkdir -p /data/uploads

EXPOSE 8080

CMD ["python", "main.py"]
