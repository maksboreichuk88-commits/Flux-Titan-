-- Create leads table for storing audio processing records
-- Run with: npm run migrate

CREATE TABLE IF NOT EXISTS leads (
    id UUID PRIMARY KEY,
    checksum VARCHAR(64) NOT NULL UNIQUE,  -- SHA-256 for idempotency
    source VARCHAR(255) NOT NULL,          -- Source identifier
    external_id VARCHAR(255),              -- Optional external reference
    original_url TEXT NOT NULL,            -- S3 URL of original Opus file
    mp3_url TEXT,                          -- S3 URL of MP3 conversion
    wav_url TEXT,                          -- S3 URL of WAV conversion
    status VARCHAR(50) NOT NULL DEFAULT 'pending',  -- pending, completed, failed
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Index for fast checksum lookups (idempotency check)
CREATE INDEX IF NOT EXISTS idx_leads_checksum ON leads(checksum);

-- Index for status queries
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);

-- Index for source filtering
CREATE INDEX IF NOT EXISTS idx_leads_source ON leads(source);

-- Index for external_id lookups
CREATE INDEX IF NOT EXISTS idx_leads_external_id ON leads(external_id) WHERE external_id IS NOT NULL;
