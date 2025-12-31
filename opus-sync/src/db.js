/**
 * PostgreSQL connection pool and helper functions
 */

import pg from 'pg';
import pino from 'pino';
import config from './config.js';

const logger = pino({ name: 'db' });

// Connection pool
const pool = new pg.Pool({
  host: config.db.host,
  port: config.db.port,
  database: config.db.database,
  user: config.db.user,
  password: config.db.password,
  max: 20,
  idleTimeoutMillis: 30000,
});

pool.on('error', (err) => {
  logger.error({ err }, 'Unexpected error on idle client');
});

/**
 * Execute a query with parameters
 */
export async function query(text, params) {
  const start = Date.now();
  const res = await pool.query(text, params);
  const duration = Date.now() - start;
  logger.debug({ text, duration, rows: res.rowCount }, 'Executed query');
  return res;
}

/**
 * Get a client for transactions
 */
export async function getClient() {
  return pool.connect();
}

/**
 * Create a new lead record
 */
export async function createLead({ id, checksum, source, externalId, originalUrl }) {
  const result = await query(
    `INSERT INTO leads (id, checksum, source, external_id, original_url, status, created_at, updated_at)
     VALUES ($1, $2, $3, $4, $5, 'pending', NOW(), NOW())
     RETURNING *`,
    [id, checksum, source, externalId, originalUrl]
  );
  return result.rows[0];
}

/**
 * Find lead by checksum (for idempotency)
 */
export async function findLeadByChecksum(checksum) {
  const result = await query('SELECT * FROM leads WHERE checksum = $1', [checksum]);
  return result.rows[0] || null;
}

/**
 * Find lead by ID
 */
export async function findLeadById(id) {
  const result = await query('SELECT * FROM leads WHERE id = $1', [id]);
  return result.rows[0] || null;
}

/**
 * Update lead after transcoding
 */
export async function updateLeadTranscoded(id, { mp3Url, wavUrl, status }) {
  const result = await query(
    `UPDATE leads 
     SET mp3_url = $2, wav_url = $3, status = $4, updated_at = NOW()
     WHERE id = $1
     RETURNING *`,
    [id, mp3Url, wavUrl, status]
  );
  return result.rows[0];
}

/**
 * Update lead status (for errors)
 */
export async function updateLeadStatus(id, status) {
  const result = await query(
    `UPDATE leads SET status = $1, updated_at = NOW() WHERE id = $2 RETURNING *`,
    [status, id]
  );
  return result.rows[0];
}

export async function closePool() {
  await pool.end();
}

export default { query, getClient, createLead, findLeadByChecksum, findLeadById, updateLeadTranscoded, updateLeadStatus, closePool };