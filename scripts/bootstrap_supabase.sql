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

-- Webhook idempotency: WhatsApp redelivers messages when a response is slow;
-- claiming the message id here makes every delivery after the first a no-op.
CREATE TABLE IF NOT EXISTS processed_messages (
    message_id TEXT PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
