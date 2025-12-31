/**
 * Express application setup
 * Exports app for testing, actual server start in index.js
 */

import express from 'express';
import pino from 'pino';
import uploadRouter from './routes/upload.js';
import statusRouter from './routes/status.js';
import downloadRouter from './routes/download.js';
import { errorHandler, notFoundHandler } from './middleware/errorHandler.js';

const logger = pino({ name: 'app' });

const app = express();

// Middleware
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Request logging
app.use((req, res, next) => {
  const start = Date.now();
  res.on('finish', () => {
    logger.info({
      method: req.method,
      url: req.url,
      status: res.statusCode,
      duration: Date.now() - start,
    }, 'Request completed');
  });
  next();
});

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// Routes
app.use('/upload', uploadRouter);
app.use('/status', statusRouter);
app.use('/download', downloadRouter);

// Error handlers
app.use(notFoundHandler);
app.use(errorHandler);

export default app;