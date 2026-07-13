-- Fintra chat-history schema.
-- Run this once in the Supabase dashboard: SQL Editor -> New query -> paste -> Run.

CREATE TABLE IF NOT EXISTS chat_history (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(50) NOT NULL,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_history_session ON chat_history(session_id);
