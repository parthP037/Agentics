-- SQLite Memory Schema
-- ABC Technologies Customer Support Automation System
-- Task 7: SQLite-Based Memory

-- Create conversation history table
CREATE TABLE IF NOT EXISTS conversation_history (
    id            INTEGER  PRIMARY KEY AUTOINCREMENT,
    customer_id   TEXT     NOT NULL,
    customer_name TEXT,
    role          TEXT     NOT NULL CHECK (role IN ('user', 'assistant')),
    message       TEXT     NOT NULL,
    intent        TEXT     CHECK (intent IN ('Sales', 'Technical', 'Billing', 'Account', 'Memory')),
    timestamp     TEXT     NOT NULL
);

-- Index for fast customer lookup
CREATE INDEX IF NOT EXISTS idx_customer_id
    ON conversation_history (customer_id);

-- Index for time-ordered retrieval
CREATE INDEX IF NOT EXISTS idx_timestamp
    ON conversation_history (customer_id, timestamp DESC);

-- Example data — demonstrating memory recall (Query 5 scenario)
-- Customer David contacts billing, then later asks about previous issue:
INSERT INTO conversation_history (customer_id, customer_name, role, message, intent, timestamp)
VALUES
    ('CUST_004', 'David', 'user',      'I need a refund for my annual subscription.', 'Billing',  '2026-06-28T10:00:00'),
    ('CUST_004', 'David', 'assistant', 'Your refund request has been received and flagged for supervisor review.', 'Billing', '2026-06-28T10:00:01'),
    ('CUST_004', 'David', 'user',      'What was my previous support issue?', 'Memory',   '2026-06-28T10:05:00'),
    ('CUST_004', 'David', 'assistant', 'Based on your history, you previously raised a refund request for your annual subscription.', 'Memory', '2026-06-28T10:05:01');

-- Query to retrieve a customer's history (used in sqlite_memory.py)
-- SELECT role, message, intent, timestamp, customer_name
-- FROM conversation_history
-- WHERE customer_id = ?
-- ORDER BY timestamp DESC
-- LIMIT 10;
