-- PostgreSQL schema for FantomAI Lead Management (Supabase)
-- Run this in your Supabase SQL editor to set up the database.

CREATE TABLE IF NOT EXISTS leads (
    id VARCHAR(30) PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(50) DEFAULT '',
    company VARCHAR(255) DEFAULT '',
    message TEXT NOT NULL,
    source VARCHAR(100) DEFAULT 'Web Form',
    ai_analysis JSONB DEFAULT '{}'::jsonb,
    read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_leads_timestamp ON leads(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_leads_email ON leads(email);
CREATE INDEX IF NOT EXISTS idx_leads_read ON leads(read);
CREATE INDEX IF NOT EXISTS idx_leads_source ON leads(source);

-- GIN index for JSONB queries on ai_analysis fields
CREATE INDEX IF NOT EXISTS idx_leads_ai_analysis ON leads USING GIN (ai_analysis);

-- ============================================================
-- Appointments table for "Book an Appointment" feature
-- ============================================================
CREATE TABLE IF NOT EXISTS appointments (
    id VARCHAR(30) PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    appointment_date DATE NOT NULL,
    time_window VARCHAR(100) NOT NULL,
    automation_goal TEXT NOT NULL DEFAULT '',
    read BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_appointments_created_at ON appointments(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_appointments_email ON appointments(email);
CREATE INDEX IF NOT EXISTS idx_appointments_date ON appointments(appointment_date);
CREATE INDEX IF NOT EXISTS idx_appointments_read ON appointments(read);
