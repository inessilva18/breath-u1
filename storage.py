# storage.py
import sqlite3
from typing import Optional, Dict, Any
import json

DB_PATH = "interactions.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS interactions (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      text TEXT,
      emotion_json TEXT,
      recommendations_json TEXT,
      rating INTEGER
    )
    """)
    conn.commit()
    conn.close()

def save_interaction(text: str, emotion: Dict[str, Any], recommendations: Dict[str, Any], rating: Optional[int] = None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO interactions (text, emotion_json, recommendations_json, rating) VALUES (?, ?, ?, ?)",
              (text, json.dumps(emotion, ensure_ascii=False), json.dumps(recommendations, ensure_ascii=False), rating))
    conn.commit()
    conn.close()
