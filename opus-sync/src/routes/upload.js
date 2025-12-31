/**
 * POST /upload endpoint
 * 
 * Accepts multipart/form-data with:
 * - file: Opus audio file (required)
 * - source: String identifier for the source (required)
 * - external_id: Optional external identifier
 */

import { Router } from 'express';
import multer from 'multer';
import { v4 as uuidv4 } from 'uuid';
import pino from 'pino';
import { tmpdir } from 'os';
import { join } from 'path';
import { existsSync, mkdirSync } from 'fs';
import { validateOpus, cleanupFile } from '../services/ffmpeg.js';
import { computeSha256 } from '../services/hash.js';
import { uploadFile, generateKey } from '../services/s3.js';
import { addTranscodeJob } from '../queue/queue.js';
import db from '../db.js';

const router = Router();
const logger = pino({ name: 'upload' });

// Ensure temporary upload directory exists (uses OS temp directory)
const uploadDir = join(tmpdir(), 'opus-uploads');
if (!existsSync(uploadDir)) mkdirSync(uploadDir, { recursive: true });

// Configure multer for temp file storage
const upload = multer({
  dest: uploadDir,
  limits: {
    fileSize: 100 * 1024 * 1024, // 100MB max
  },
});

router.post('/', upload.single('file'), async (req, res, next) => {
  const uploadedFile = req.file;
  
  try {
    // Validate required fields
    if (!uploadedFile) {
      return res.status(400).json({ 
        error: 'Missing file', 
        message: 'Please provide an audio file in the "file" field' 
      });
    }

    const { source, external_id: externalId } = req.body;
    
    if (!source) {
      await cleanupFile(uploadedFile.path);
      return res.status(400).json({ 
        error: 'Missing source', 
        message: 'Please provide a "source" field' 
      });
    }

    // Step 1: Validate Opus format using ffprobe
    logger.info({ originalName: uploadedFile.originalname }, 'Validating file format');
    const validation = await validateOpus(uploadedFile.path);
    
    if (!validation.valid) {
      await cleanupFile(uploadedFile.path);
      return res.status(400).json({
        error: 'Invalid format',
        message: validation.error,
        details: 'Only Opus audio files are accepted'
      });
    }

    // Step 2: Compute SHA-256 for idempotency check
    const checksum = await computeSha256(uploadedFile.path);
    logger.info({ checksum }, 'Computed file checksum');

    // Step 3: Check for existing record (idempotency)
    const existingLead = await db.findLeadByChecksum(checksum);
    
    if (existingLead) {
      logger.info({ id: existingLead.id, checksum }, 'Found existing record, returning cached result');
      await cleanupFile(uploadedFile.path);
      
      return res.status(200).json({
        id: existingLead.id,
        status: existingLead.status,
        original_url: existingLead.original_url,
        checksum: existingLead.checksum,
        cached: true,
      });
    }

    // Step 4: Generate ID and upload original to S3
    const leadId = uuidv4();
    const extension = 'opus'; // Store as .opus regardless of container
    const originalKey = generateKey(leadId, 'original', extension);
    
    logger.info({ leadId, originalKey }, 'Uploading original to S3');
    const originalUrl = await uploadFile(uploadedFile.path, originalKey, 'audio/opus');

    // Step 5: Create database record
    const lead = await db.createLead({
      id: leadId,
      checksum,
      source,
      externalId: externalId || null,
      originalUrl,
    });

    // Step 6: Queue transcode job
    await addTranscodeJob({
      leadId,
      originalKey,
    });

    logger.info({ leadId, checksum }, 'Upload processed successfully');

    // Cleanup temp file after S3 upload
    await cleanupFile(uploadedFile.path);

    return res.status(201).json({
      id: lead.id,
      status: lead.status,
      original_url: lead.original_url,
      checksum: lead.checksum,
    });

  } catch (error) {
    // Cleanup on error
    if (uploadedFile) {
      await cleanupFile(uploadedFile.path);
    }
    next(error);
  }
});

export default router;