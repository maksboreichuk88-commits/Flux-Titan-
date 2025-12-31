/**
 * Global error handler middleware
 * Logs errors and returns readable messages
 */

import pino from 'pino';

const logger = pino({ name: 'error-handler' });

export function errorHandler(err, req, res, next) {
  // Log full error with stack trace
  logger.error({
    err,
    method: req.method,
    url: req.url,
    body: req.body,
    query: req.query,
  }, 'Request error');

  // Determine status code
  const statusCode = err.statusCode || err.status || 500;

  // Build response
  const response = {
    error: err.name || 'Error',
    message: err.message || 'An unexpected error occurred',
  };

  // In development, include stack trace
  if (process.env.NODE_ENV === 'development') {
    response.stack = err.stack;
  }

  res.status(statusCode).json(response);
}

export function notFoundHandler(req, res) {
  res.status(404).json({
    error: 'Not Found',
    message: `Route ${req.method} ${req.url} not found`
  });
}