import json
import sqlite3
import os

DB_PATH = 'data/wellbeing.db'
JSON_PATH = 'data/history.json'

def migrate():
    if not os.path.exists(JSON_PATH):
        print("No history.json found.")
        return

    with open(JSON_PATH, 'r') as f:
        data = json.load(f)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Ensure table exists (though app.py should have created it)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            user_text TEXT,
            gender TEXT,
            age TEXT,
            prediction TEXT,
            confidence TEXT,
            posterior_probs TEXT,
            summary TEXT,
            tips TEXT,
            affirmation TEXT,
            is_crisis INTEGER DEFAULT 0
        )
    ''')

    count = 0
    for entry in data:
        # Check if already exists to avoid duplicates
        cursor.execute("SELECT id FROM assessments WHERE timestamp = ?", (entry['timestamp'],))
        if cursor.fetchone():
            continue

        cursor.execute('''
            INSERT INTO assessments (
                timestamp, user_text, gender, age, prediction, 
                confidence, posterior_probs, summary, tips, affirmation, is_crisis
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            entry.get('timestamp'),
            entry.get('user_text'),
            entry.get('gender'),
            entry.get('age'),
            entry.get('prediction'),
            entry.get('confidence'),
            json.dumps(entry.get('posteriorProbs', {})),
            "Historical data from JSON migration.",
            "[]",
            "I am moving forward with clarity.",
            0
        ))
        count += 1

    conn.commit()
    conn.close()
    print(f"Successfully migrated {count} records from history.json to wellbeing.db.")

if __name__ == "__main__":
    migrate()
