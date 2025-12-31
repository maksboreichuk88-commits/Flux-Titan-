/**
 * Application entry point
 * Starts the HTTP server
 */

import pino from 'pino';
import app from './app.js';
import config from './config.js';
import db from './db.js';
import { closeQueue } from './queue/queue.js';

const logger = pino({ 
  name: 'server',
  level: process.env.LOG_LEVEL || 'info'
});

// Start server
const server = app.listen(config.port, () => {
  logger.info({ port: config.port, env: config.nodeEnv }, 'Server started');
});

// Graceful shutdown
async function shutdown(signal) {
  logger.info({ signal }, 'Shutdown signal received');
  
  server.close(async () => {
    logger.info('HTTP server closed');
    
    try {
      await closeQueue();
      await db.closePool();
      logger.info('All connections closed');
      process.exit(0);
    } catch (err) {
      logger.error({ err }, 'Error during shutdown');
      process.exit(1);
    }
  });

  // Force exit after 30s
  setTimeout(() => {
    logger.error('Forced shutdown after timeout');
    process.exit(1);
  }, 30000);
}

process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT', () => shutdown('SIGINT'));
