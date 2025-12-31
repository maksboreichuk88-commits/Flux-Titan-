/**
 * S3/MinIO client for file storage
 */

import { S3Client, PutObjectCommand, GetObjectCommand, HeadObjectCommand } from '@aws-sdk/client-s3';
import { Upload } from '@aws-sdk/lib-storage';
import { createReadStream } from 'fs';
import { stat } from 'fs/promises';
import pino from 'pino';
import config from '../config.js';

const logger = pino({ name: 's3' });

// Initialize S3 client (works with MinIO too)
const s3Client = new S3Client({
  endpoint: config.s3.endpoint,
  region: config.s3.region,
  credentials: {
    accessKeyId: config.s3.accessKeyId,
    secretAccessKey: config.s3.secretAccessKey,
  },
  forcePathStyle: config.s3.forcePathStyle, // Required for MinIO
});

/**
 * Generate S3 key for a file
 */
export function generateKey(leadId, type, extension) {
  // Structure: leads/{id}/{type}.{ext}
  return `leads/${leadId}/${type}.${extension}`;
}

/**
 * Upload a file to S3
 * Uses multipart upload for large files
 * 
 * @param {string} filePath - Local file path
 * @param {string} key - S3 object key
 * @param {string} contentType - MIME type
 * @returns {Promise<string>} - Public URL to the object
 */
export async function uploadFile(filePath, key, contentType) {
  const fileStats = await stat(filePath);
  const fileStream = createReadStream(filePath);

  logger.info({ key, size: fileStats.size, contentType }, 'Uploading to S3');

  // Use multipart upload for reliability
  const upload = new Upload({
    client: s3Client,
    params: {
      Bucket: config.s3.bucket,
      Key: key,
      Body: fileStream,
      ContentType: contentType,
    },
    // 5MB parts, up to 4 concurrent uploads
    partSize: 5 * 1024 * 1024,
    queueSize: 4,
  });

  await upload.done();

  // Return the URL (adjust for production S3 vs MinIO)
  const url = `${config.s3.endpoint}/${config.s3.bucket}/${key}`;
  logger.info({ key, url }, 'Upload complete');
  
  return url;
}

/**
 * Get a readable stream from S3
 */
export async function getFileStream(key) {
  const command = new GetObjectCommand({
    Bucket: config.s3.bucket,
    Key: key,
  });

  const response = await s3Client.send(command);
  return response.Body;
}

/**
 * Check if object exists
 */
export async function objectExists(key) {
  try {
    await s3Client.send(new HeadObjectCommand({
      Bucket: config.s3.bucket,
      Key: key,
    }));
    return true;
  } catch (err) {
    // Different SDKs and S3-compatible servers can return different error shapes.
    // Treat 404 / NotFound / NoSuchKey as object-not-exist (return false), otherwise rethrow.
    const status = err?.$metadata?.httpStatusCode || err?.statusCode || err?.status;
    if (status === 404 || err?.name === 'NotFound' || err?.Code === 'NoSuchKey') return false;
    throw err;
  }
}

/**
 * Get signed URL for download (if needed for private buckets)
 */
export function getPublicUrl(key) {
  return `${config.s3.endpoint}/${config.s3.bucket}/${key}`;
}

export { s3Client };