/**
 * FFmpeg/FFprobe utilities for validation and transcoding
 * 
 * IMPORTANT: ffmpeg and ffprobe must be installed on the system
 * and available in PATH (or configured via FFMPEG_PATH/FFPROBE_PATH)
 */

import { spawn } from 'child_process';
import { createReadStream, createWriteStream } from 'fs';
import { unlink } from 'fs/promises';
import { tmpdir } from 'os';
import { join } from 'path';
import { v4 as uuidv4 } from 'uuid';
import pino from 'pino';
import config from '../config.js';

const logger = pino({ name: 'ffmpeg' });

/**
 * Run ffprobe and get stream info as JSON
 * Used to validate that file is actually Opus codec in ogg/webm/mkv container
 */
export async function probeFile(filePath) {
  return new Promise((resolve, reject) => {
    const args = [
      '-v', 'quiet',           // Suppress banner/logs
      '-print_format', 'json', // Output as JSON
      '-show_streams',         // Show stream info
      '-show_format',          // Show container format
      filePath
    ];

    const proc = spawn(config.ffmpeg.ffprobePath, args);
    let stdout = '';
    let stderr = '';

    proc.stdout.on('data', (data) => { stdout += data; });
    proc.stderr.on('data', (data) => { stderr += data; });

    proc.on('close', (code) => {
      if (code !== 0) {
        logger.error({ code, stderr }, 'ffprobe failed');
        return reject(new Error(`ffprobe exited with code ${code}`));
      }
      try {
        resolve(JSON.parse(stdout));
      } catch (e) {
        reject(new Error('Failed to parse ffprobe output'));
      }
    });

    proc.on('error', reject);
  });
}

/**
 * Validate that the file contains Opus audio codec
 * Accepts Opus in various containers: ogg, webm, mkv, etc.
 * 
 * @returns {{ valid: boolean, error?: string, codec?: string, container?: string }}
 */
export async function validateOpus(filePath) {
  try {
    const info = await probeFile(filePath);

    // Check if we have any audio streams
    const audioStreams = (info.streams || []).filter(s => s.codec_type === 'audio');
    
    if (audioStreams.length === 0) {
      return { valid: false, error: 'No audio streams found in file' };
    }

    // Check if any audio stream is Opus
    const opusStream = audioStreams.find(s => s.codec_name === 'opus');
    
    if (!opusStream) {
      const codecs = audioStreams.map(s => s.codec_name).join(', ');
      return { 
        valid: false, 
        error: `Audio codec is not Opus. Found: ${codecs}`,
        codec: codecs
      };
    }

    return { 
      valid: true, 
      codec: 'opus',
      container: info.format?.format_name || 'unknown'
    };
  } catch (error) {
    logger.error({ error }, 'Validation error');
    return { valid: false, error: error.message };
  }
}

/**
 * Transcode audio file to specified format using FFmpeg
 * 
 * Supported formats:
 * - mp3: libmp3lame, 192k bitrate
 * - wav: PCM 16-bit, 44.1kHz
 * 
 * @param {string} inputPath - Input file path
 * @param {'mp3'|'wav'} format - Output format
 * @returns {Promise<string>} - Path to transcoded file (caller must clean up)
 */
export async function transcode(inputPath, format) {
  const outputPath = join(tmpdir(), `${uuidv4()}.${format}`);

  // FFmpeg arguments for each format
  // Using high-quality settings suitable for production
  const formatArgs = {
    mp3: [
      '-codec:a', 'libmp3lame',  // MP3 encoder
      '-b:a', '192k',            // Bitrate
      '-ar', '44100',            // Sample rate
    ],
    wav: [
      '-codec:a', 'pcm_s16le',   // 16-bit PCM
      '-ar', '44100',            // Sample rate
    ],
  };

  if (!formatArgs[format]) {
    throw new Error(`Unsupported format: ${format}`);
  }

  return new Promise((resolve, reject) => {
    const args = [
      '-y',                      // Overwrite output
      '-i', inputPath,           // Input file
      '-vn',                     // No video
      ...formatArgs[format],     // Format-specific args
      outputPath                 // Output file
    ];

    logger.info({ inputPath, format, outputPath }, 'Starting transcode');

    const proc = spawn(config.ffmpeg.ffmpegPath, args);
    let stderr = '';

    proc.stderr.on('data', (data) => { stderr += data; });

    proc.on('close', (code) => {
      if (code !== 0) {
        logger.error({ code, stderr }, 'FFmpeg transcode failed');
        return reject(new Error(`FFmpeg exited with code ${code}: ${stderr.slice(-200)}`));
      }
      logger.info({ outputPath }, 'Transcode complete');
      resolve(outputPath);
    });

    proc.on('error', (err) => {
      logger.error({ err }, 'FFmpeg spawn error');
      reject(err);
    });
  });
}

/**
 * Clean up temporary files
 */
export async function cleanupFile(filePath) {
  try {
    await unlink(filePath);
  } catch (err) {
    logger.warn({ err, filePath }, 'Failed to cleanup temp file');
  }
}