# Multi-stage build for Node.js application

# Stage 1: Builder
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install all dependencies (including devDependencies for build)
RUN npm ci

# Copy source code
COPY . .

# Stage 2: Production
FROM node:20-alpine AS production

# Install ffmpeg and curl for healthcheck
RUN apk add --no-cache ffmpeg curl

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install production dependencies only
RUN npm ci --only=production

# Copy source code from builder
COPY --from=builder /app/src ./src
COPY --from=builder /app/migrations ./migrations
COPY --from=builder /app/scripts ./scripts

# Create non-root user
RUN addgroup -g 1001 -S appgroup && \
    adduser -S appuser -u 1001 -G appgroup

# Create temp directories with proper permissions
RUN mkdir -p /tmp/opus-uploads && \
    chown -R appuser:appgroup /tmp/opus-uploads

USER appuser

# Expose port
EXPOSE 3000

# Health check (use curl which is available in the image)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/health || exit 1

# Default command (can be overridden for worker)
CMD ["node", "src/index.js"]