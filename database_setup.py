# database_setup.py
import sqlite3

# Connect to the SQLite database (this will create the file if it doesn't exist)
conn = sqlite3.connect('emails.db')
cursor = conn.cursor()

# SQL statement to create a table with all necessary columns
create_table_query = """
CREATE TABLE IF NOT EXISTS emails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gmail_msg_id TEXT NOT NULL UNIQUE,
    sender TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT,
    received_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    sentiment TEXT,
    priority TEXT,
    customer_request TEXT,
    contact_info TEXT,
    generated_response TEXT
);
"""

# Execute the query
cursor.execute(create_table_query)

# Commit the changes and close the connection
conn.commit()
conn.close()

print("Database 'emails.db' and table 'emails' with full schema created successfully.")