/**
 * GET /status/:id endpoint
 * Returns lead record with all available URLs
 */

import { Router } from 'express';
import db from '../db.js';

const router = Router();

router.get('/:id', async (req, res, next) => {
  try {
    const { id } = req.params;

    // Validate UUID format (basic check)
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

    // Format response
    return res.json({
      id: lead.id,
      checksum: lead.checksum,
      source: lead.source,
      external_id: lead.external_id,
      status: lead.status,
      original_url: lead.original_url,
      mp3_url: lead.mp3_url,
      wav_url: lead.wav_url,
      created_at: lead.created_at,
      updated_at: lead.updated_at,
    });

  } catch (error) {
    next(error);
  }
});

export default router;