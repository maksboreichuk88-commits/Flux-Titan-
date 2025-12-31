/**
 * BullMQ Worker for transcoding jobs
 * 
 * Processes: Original Opus → MP3, WAV
 * Uploads results to S3 and updates database
 * 
 * Run separately: npm run worker
 */

import { Worker } from 'bullmq';
import { createWriteStream } from 'fs';
import { unlink, mkdtemp, rm } from 'fs/promises';
import { tmpdir } from 'os';
import { join } from 'path';
import { pipeline } from 'stream/promises';
import pino from 'pino';
import config from '../config.js';
import { redisConnection } from './queue.js';
import { transcode, cleanupFile } from '../services/ffmpeg.js';
import { uploadFile, getFileStream, generateKey } from '../services/s3.js';
import db from '../db.js';

const logger = pino({ 
  name: 'worker',
  level: process.env.LOG_LEVEL || 'info'
});

/**
 * Process a transcode job
 * 
 * Steps:
 * 1. Download original from S3 to temp file
 * 2. Transcode to MP3
 * 3. Transcode to WAV
 * 4. Upload both to S3
 * 5. Update database with URLs
 * 6. Cleanup temp files
 */
async function processTranscodeJob(job) {
  const { leadId, originalKey } = job.data;
  
  logger.info({ leadId, originalKey, attempt: job.attemptsMade + 1 }, 'Processing transcode job');

  // Create temp directory for this job
  const tempDir = await mkdtemp(join(tmpdir(), 'opus-sync-'));
  const originalPath = join(tempDir, 'original.opus');
  let mp3Path = null;
  let wavPath = null;

  try {
    // Step 1: Download original from S3
    logger.info({ leadId }, 'Downloading original from S3');
    const stream = await getFileStream(originalKey);
    await pipeline(stream, createWriteStream(originalPath));

    // Step 2: Transcode to MP3
    logger.info({ leadId }, 'Transcoding to MP3');
    mp3Path = await transcode(originalPath, 'mp3');

    // Step 3: Transcode to WAV
    logger.info({ leadId }, 'Transcoding to WAV');
    wavPath = await transcode(originalPath, 'wav');

    // Step 4: Upload to S3
    const mp3Key = generateKey(leadId, 'converted', 'mp3');
    const wavKey = generateKey(leadId, 'converted', 'wav');

    logger.info({ leadId }, 'Uploading transcoded files to S3');
    const [mp3Url, wavUrl] = await Promise.all([
      uploadFile(mp3Path, mp3Key, 'audio/mpeg'),
      uploadFile(wavPath, wavKey, 'audio/wav'),
    ]);

    // Step 5: Update database
    await db.updateLeadTranscoded(leadId, {
      mp3Url,
      wavUrl,
      status: 'completed',
    });

    logger.info({ leadId, mp3Url, wavUrl }, 'Transcode job completed successfully');

    return { mp3Url, wavUrl };

  } catch (error) {
    logger.error({ leadId, error: error.message, attempt: job.attemptsMade + 1 }, 'Transcode job failed');
    
    // If this was the last attempt, mark as failed in DB
    if (job.attemptsMade + 1 >= config.queue.attempts) {
      await db.updateLeadStatus(leadId, 'failed');
    }
    
    throw error; // Re-throw for BullMQ retry logic

  } finally {
    // Step 6: Cleanup temp files
    await cleanupFile(originalPath);
    if (mp3Path) await cleanupFile(mp3Path);
    if (wavPath) await cleanupFile(wavPath);
    
    try {
      // Use rm with recursive+force to ensure temp dir is removed on all platforms
      await rm(tempDir, { recursive: true, force: true });
    } catch (e) {
      logger.warn({ err: e, tempDir }, 'Failed to remove temp directory');
    }
  }
}

// Create worker instance
const worker = new Worker(
  config.queue.name,
  processTranscodeJob,
  {
    connection: redisConnection,
    concurrency: parseInt(process.env.WORKER_CONCURRENCY || '2', 10),
  }
);

// Worker event handlers
worker.on('completed', (job, result) => {
  logger.info({ jobId: job.id, leadId: job.data.leadId }, 'Job completed');
});

worker.on('failed', (job, err) => {
  logger.error(
    { jobId: job?.id, leadId: job?.data?.leadId, error: err.message, attempts: job?.attemptsMade },
    'Job failed'
  );
});

worker.on('error', (err) => {
  logger.error({ error: err.message }, 'Worker error');
});

// Graceful shutdown
async function shutdown() {
  logger.info('Shutting down worker...');
  await worker.close();
  await redisConnection.quit();
  await db.closePool();
  process.exit(0);
}

process.on('SIGTERM', shutdown);
process.on('SIGINT', shutdown);

logger.info('Worker started and waiting for jobs...');