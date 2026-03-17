-- Create conversation and message tables for storing user chat history.
-- Run against your database, e.g.: psql -U your_user -d hr_project_database -f create_conversation_message_tables.sql
-- PostgreSQL.

-- Conversation: one per user chat thread
CREATE TABLE IF NOT EXISTS conversation (
    id SERIAL PRIMARY KEY,
    user_account_id INTEGER NOT NULL REFERENCES user_account(id) ON DELETE CASCADE,
    title VARCHAR(255) NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_conversation_user_account_id ON conversation(user_account_id);

-- Message: individual messages in a conversation
CREATE TABLE IF NOT EXISTS message (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversation(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_message_conversation_id ON message(conversation_id);
CREATE INDEX IF NOT EXISTS ix_message_role ON message(role);
