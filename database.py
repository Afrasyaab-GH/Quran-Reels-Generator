"""
Database layer — SQLite schema, initialization, and all CRUD operations.
"""
import os
import time
import json
import shutil
import sqlite3
from flask import g
from config import DB_PATH


def get_db():
    """Get database connection for current request"""
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(exception):
    """Close database connection at end of request"""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """Initialize database tables with session support"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Jobs table - for persistence across restarts (مع دعم session_id)
    c.execute('''CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY,
        status TEXT NOT NULL DEFAULT 'pending',
        percent INTEGER DEFAULT 0,
        eta TEXT DEFAULT '--:--',
        output_path TEXT,
        error TEXT,
        should_stop INTEGER DEFAULT 0,
        created_at REAL,
        completed_at REAL,
        config_json TEXT,
        workspace TEXT,
        session_id TEXT
    )''')
    
    # History table - for user download history (مع دعم session_id)
    c.execute('''CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id TEXT,
        title TEXT,
        reciter TEXT,
        surah INTEGER,
        start_ayah INTEGER,
        end_ayah INTEGER,
        quality TEXT,
        fps TEXT,
        download_filename TEXT,
        created_at REAL,
        session_id TEXT,
        FOREIGN KEY (job_id) REFERENCES jobs(id)
    )''')
    
    # Batch jobs table - for batch export
    c.execute('''CREATE TABLE IF NOT EXISTS batch_jobs (
        id TEXT PRIMARY KEY,
        status TEXT NOT NULL DEFAULT 'pending',
        total_jobs INTEGER DEFAULT 0,
        completed_jobs INTEGER DEFAULT 0,
        failed_jobs INTEGER DEFAULT 0,
        current_job_id TEXT,
        current_job_index INTEGER DEFAULT 0,
        config_json TEXT,
        created_at REAL,
        started_at REAL,
        completed_at REAL
    )''')
    
    # Batch items table - individual jobs in a batch
    c.execute('''CREATE TABLE IF NOT EXISTS batch_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        batch_id TEXT,
        job_id TEXT,
        position INTEGER,
        surah INTEGER,
        start_ayah INTEGER,
        end_ayah INTEGER,
        status TEXT DEFAULT 'pending',
        output_path TEXT,
        error TEXT,
        created_at REAL,
        FOREIGN KEY (batch_id) REFERENCES batch_jobs(id),
        FOREIGN KEY (job_id) REFERENCES jobs(id)
    )''')
    
    # Migration: إضافة session_id للجداول القديمة لو مش موجودة
    try:
        c.execute("SELECT session_id FROM jobs LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE jobs ADD COLUMN session_id TEXT")
        print("✅ Added session_id to jobs table")
    
    try:
        c.execute("SELECT session_id FROM history LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE history ADD COLUMN session_id TEXT")
        print("✅ Added session_id to history table")
    
    # Migration: إضافة output_path و error لـ batch_items
    try:
        c.execute("SELECT output_path FROM batch_items LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE batch_items ADD COLUMN output_path TEXT")
        print("✅ Added output_path to batch_items table")
    
    try:
        c.execute("SELECT error FROM batch_items LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE batch_items ADD COLUMN error TEXT")
        print("✅ Added error to batch_items table")
    
    # Migration: إضافة video_started_at لـ batch_items
    try:
        c.execute("SELECT video_started_at FROM batch_items LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE batch_items ADD COLUMN video_started_at REAL")
        print("✅ Added video_started_at to batch_items table")
    
    # Migration: إضافة avg_video_time لـ batch_jobs
    try:
        c.execute("SELECT avg_video_time FROM batch_jobs LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE batch_jobs ADD COLUMN avg_video_time REAL")
        print("✅ Added avg_video_time to batch_jobs table")
    
    conn.commit()
    conn.close()
    print("✅ Database initialized successfully!")

# ==========================================
# 📋 Job CRUD
# ==========================================

def db_create_job(job_id, workspace, config=None, session_id=None):
    """Create a new job in database with session support"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO jobs (id, status, percent, created_at, workspace, config_json, session_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)''', 
              (job_id, 'pending', 0, time.time(), workspace, json.dumps(config) if config else None, session_id))
    conn.commit()
    conn.close()

def db_update_job(job_id, **kwargs):
    """Update job in database"""
    if not kwargs:
        return
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    set_clause = ', '.join([f"{k} = ?" for k in kwargs.keys()])
    values = list(kwargs.values()) + [job_id]
    
    c.execute(f"UPDATE jobs SET {set_clause} WHERE id = ?", values)
    conn.commit()
    conn.close()

def db_get_job(job_id):
    """Get job from database"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    row = c.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None

def db_get_all_jobs(status=None, limit=50):
    """Get all jobs, optionally filtered by status"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    if status:
        c.execute("SELECT * FROM jobs WHERE status = ? ORDER BY created_at DESC LIMIT ?", (status, limit))
    else:
        c.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,))
    
    rows = c.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def db_get_pending_jobs():
    """Get all pending/processing jobs for recovery"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM jobs WHERE status IN ('pending', 'processing')")
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# ==========================================
# 📋 History CRUD
# ==========================================

def db_add_history(job_id, title, reciter, surah, start_ayah, end_ayah, quality, fps, filename, session_id=None):
    """Add entry to history with session support"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO history (job_id, title, reciter, surah, start_ayah, end_ayah, quality, fps, download_filename, created_at, session_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (job_id, title, reciter, surah, start_ayah, end_ayah, quality, fps, filename, time.time(), session_id))
    conn.commit()
    conn.close()

def db_get_history(limit=20, session_id=None):
    """Get history entries filtered by session"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    if session_id:
        c.execute('''SELECT h.*, j.output_path, j.status 
                     FROM history h 
                     LEFT JOIN jobs j ON h.job_id = j.id 
                     WHERE h.session_id = ?
                     ORDER BY h.created_at DESC LIMIT ?''', (session_id, limit))
    else:
        c.execute('''SELECT h.*, j.output_path, j.status 
                     FROM history h 
                     LEFT JOIN jobs j ON h.job_id = j.id 
                     ORDER BY h.created_at DESC LIMIT ?''', (limit,))
    
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def db_cleanup_old_jobs(hours=24):
    """Clean up jobs older than specified hours"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    threshold = time.time() - (hours * 3600)
    
    # Get old completed jobs
    c.execute("SELECT id, workspace, output_path FROM jobs WHERE created_at < ? AND status IN ('complete', 'error', 'cancelled')", (threshold,))
    old_jobs = c.fetchall()
    
    # Clean up files
    for job in old_jobs:
        # حذف مجلد العمل المؤقت
        if job['workspace'] and os.path.exists(job['workspace']):
            try:
                shutil.rmtree(job['workspace'], ignore_errors=True)
            except:
                pass
        
        # حذف ملف الفيديو النهائي من outputs
        if job['output_path'] and os.path.exists(job['output_path']):
            try:
                os.remove(job['output_path'])
            except:
                pass
    
    # Delete from database
    c.execute("DELETE FROM jobs WHERE created_at < ? AND status IN ('complete', 'error', 'cancelled')", (threshold,))
    c.execute("DELETE FROM history WHERE created_at < ?", (threshold,))
    
    conn.commit()
    conn.close()
    print(f"🧹 Cleaned up {len(old_jobs)} old jobs and their video files")

# ==========================================
# 📦 Batch CRUD
# ==========================================

def db_create_batch(batch_id, total_jobs, config):
    """Create a new batch job in database"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO batch_jobs (id, status, total_jobs, completed_jobs, failed_jobs, config_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)''', 
              (batch_id, 'pending', total_jobs, 0, 0, json.dumps(config), time.time()))
    conn.commit()
    conn.close()

def db_update_batch(batch_id, **kwargs):
    """Update batch job in database"""
    if not kwargs:
        return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    set_clause = ', '.join([f"{k} = ?" for k in kwargs.keys()])
    values = list(kwargs.values()) + [batch_id]
    c.execute(f"UPDATE batch_jobs SET {set_clause} WHERE id = ?", values)
    conn.commit()
    conn.close()

def db_get_batch(batch_id):
    """Get batch job from database"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM batch_jobs WHERE id = ?", (batch_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def db_add_batch_item(batch_id, job_id, position, surah, start_ayah, end_ayah):
    """Add an item to batch"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO batch_items (batch_id, job_id, position, surah, start_ayah, end_ayah, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
              (batch_id, job_id, position, surah, start_ayah, end_ayah, 'pending', time.time()))
    conn.commit()
    conn.close()

def db_update_batch_item(batch_id, job_id, **kwargs):
    """Update batch item"""
    if not kwargs:
        return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    set_clause = ', '.join([f"{k} = ?" for k in kwargs.keys()])
    values = list(kwargs.values()) + [batch_id, job_id]
    c.execute(f"UPDATE batch_items SET {set_clause} WHERE batch_id = ? AND job_id = ?", values)
    conn.commit()
    conn.close()

def db_get_batch_items(batch_id):
    """Get all items in a batch"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM batch_items WHERE batch_id = ? ORDER BY position", (batch_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def db_get_pending_batches():
    """Get all pending/running batches"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM batch_jobs WHERE status IN ('pending', 'running')")
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]
