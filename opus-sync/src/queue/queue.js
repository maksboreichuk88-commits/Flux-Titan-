/**
 * BullMQ queue for transcode jobs
 * 
 * Retry policy: 3 attempts with exponential backoff (1s, 2s, 4s)
 */

import { Queue } from 'bullmq';
import IORedis from 'ioredis';
import pino from 'pino';
import config from '../config.js';

const logger = pino({ name: 'queue' });

// Redis connection for BullMQ
export const redisConnection = new IORedis({
  host: config.redis.host,
  port: config.redis.port,
  password: config.redis.password,
  maxRetriesPerRequest: null, // Required by BullMQ
});

// Transcode queue
export const transcodeQueue = new Queue(config.queue.name, {
  connection: redisConnection,
  defaultJobOptions: {
    // Retry policy: 3 attempts with exponential backoff
    // Delay sequence: 1000ms, 2000ms, 4000ms
    attempts: config.queue.attempts,
    backoff: config.queue.backoff,
    removeOnComplete: {
      age: 3600,    // Keep completed jobs for 1 hour
      count: 1000,  // Keep last 1000 completed jobs
    },
    removeOnFail: {
      age: 86400,   // Keep failed jobs for 24 hours
    },
  },
});

/**
 * Add a transcode job to the queue
 * 
 * @param {object} data - Job data
 * @param {string} data.leadId - Lead ID
 * @param {string} data.originalKey - S3 key of original file
 * @param {string} data.originalPath - Local path to original file (if still exists)
 */
export async function addTranscodeJob(data) {
  const job = await transcodeQueue.add('transcode', data, {
    jobId: `transcode-${data.leadId}`, // Prevent duplicate jobs
  });
  
  logger.info({ jobId: job.id, leadId: data.leadId }, 'Added transcode job');
  return job;
}

export async function closeQueue() {
  await transcodeQueue.close();
  await redisConnection.quit();
}