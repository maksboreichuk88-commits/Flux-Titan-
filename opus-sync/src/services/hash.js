/**
 * Compute SHA-256 hash for file content (for idempotency check)
 */

import { createHash } from 'crypto';
import { createReadStream } from 'fs';

/**
 * Calculate SHA-256 checksum of a file
 * @param {string} filePath - Path to file
 * @returns {Promise<string>} - Hex-encoded SHA-256 hash
 */
export async function computeSha256(filePath) {
  return new Promise((resolve, reject) => {
    const hash = createHash('sha256');
    const stream = createReadStream(filePath);

    stream.on('data', (chunk) => hash.update(chunk));
    stream.on('end', () => resolve(hash.digest('hex')));
    stream.on('error', reject);
  });
}

/**
 * Calculate SHA-256 from buffer
 */
export function computeSha256Buffer(buffer) {
  return createHash('sha256').update(buffer).digest('hex');
}