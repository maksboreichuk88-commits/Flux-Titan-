/**
 * GET /download/:id endpoint
 * 
 * Query params:
 * - format: mp3 | wav | original (default: original)
 * 
 * Streams file from S3 or redirects to S3 URL
 */

import { Router } from 'express';
import pino from 'pino';
import db from '../db.js';
import { getFileStream, generateKey, getPublicUrl } from '../services/s3.js';

const router = Router();
const logger = pino({ name: 'download' });

// Content-Type mapping
const contentTypes = {
  original: 'audio/opus',
  mp3: 'audio/mpeg',
  wav: 'audio/wav',
};

router.get('/:id', async (req, res, next) => {
  try {
    const { id } = req.params;
    const format = req.query.format || 'original';

    // Validate format
    if (!['original', 'mp3', 'wav'].includes(format)) {
      return res.status(400).json({
        error: 'Invalid format',
        message: 'Format must be one of: original, mp3, wav'
      });
    }

    // Validate UUID format
    if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id)) {
      return res.status(400).json({
        error: 'Invalid ID',
        message: 'Please provide a valid UUID'
      });
    }

    const lead = await db.findLeadById(id);

    if (!lead) {
      return res.status(404).json({
        error: 'Not found',
        message: `Lead with id ${id} not found`
      });
    }

    // Get appropriate URL based on format
    let url;
    let key;
    
    switch (format) {
      case 'mp3':
        if (!lead.mp3_url) {
          return res.status(404).json({
            error: 'Not ready',
            message: 'MP3 version is not yet available',
            status: lead.status
          });
        }
        key = generateKey(id, 'converted', 'mp3');
        break;
        
      case 'wav':
        if (!lead.wav_url) {
          return res.status(404).json({
            error: 'Not ready',
            message: 'WAV version is not yet available',
            status: lead.status
          });
        }
        key = generateKey(id, 'converted', 'wav');
        break;
        
      default:
        key = generateKey(id, 'original', 'opus');
    }

    // Option 1: Redirect to S3 URL
    if (req.query.redirect === 'true') {
      return res.redirect(302, getPublicUrl(key));
    }

    // Option 2: Stream from S3 through our server
    logger.info({ id, format, key }, 'Streaming file');
    
    const stream = await getFileStream(key);
    
    res.setHeader('Content-Type', contentTypes[format]);
    res.setHeader('Content-Disposition', `attachment; filename="${id}.${format === 'original' ? 'opus' : format}"`);
    
    stream.pipe(res);

  } catch (error) {
    if (error.name === 'NoSuchKey') {
      return res.status(404).json({
        error: 'File not found',
        message: 'The requested file was not found in storage'
      });
    }
    next(error);
  }
});

export default router;