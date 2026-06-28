CREATE DATABASE lead_server;
SHOW DATABASES;
USE lead_server;
CREATE USER 'moaz'@'localhost' IDENTIFIED BY '1234';
SELECT USER();

CREATE TABLE leads (
    id VARCHAR(30) PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    name VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),
    company VARCHAR(255),
    message TEXT,
    source VARCHAR(100)
);
CREATE TABLE lead_ai_analysis (
    lead_id VARCHAR(30) PRIMARY KEY,
    urgency VARCHAR(20),
    urgency_rationale TEXT,
    category VARCHAR(100),
    summary TEXT,
    draft_reply TEXT,
    ai_status VARCHAR(100),

    CONSTRAINT fk_lead
        FOREIGN KEY (lead_id)
        REFERENCES leads(id)
        ON DELETE CASCADE
);
SELECT* FROM leads;
select from* leads 