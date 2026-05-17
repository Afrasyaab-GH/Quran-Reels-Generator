"""
Quran Reels Generator — Application Entrypoint
Slim main.py that wires together all modules and starts the server.
"""
import os
import sys
import time
import json
import sqlite3
import threading

# Patch for older PIL versions if needed
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

# ==========================================
# 📦 Import Modules
# ==========================================
import config  # noqa: F401 — triggers FFmpeg/ImageMagick/dir setup on import
from config import EXEC_DIR, DB_PATH, IS_HUGGINGFACE

from flask import Flask
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from database import init_db, close_db, db_get_pending_jobs, db_update_job, db_get_pending_batches, db_update_batch
from jobs import JOBS, JOBS_LOCK
from routes import register_routes, recover_pending_jobs, background_cleanup
from youtube_integration import register_youtube_routes
from batch import register_batch_routes, recover_pending_batches, process_batch_queue

# ==========================================
# 🏗️ Create Flask Application
# ==========================================
app = Flask(__name__, static_folder=EXEC_DIR)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# 🛡️ Rate Limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["5000 per day", "1000 per hour"],
    storage_uri="memory://",
)

app.teardown_appcontext(close_db)

# ==========================================
# 🔌 Register Routes
# ==========================================
register_routes(app, limiter)
register_youtube_routes(app, limiter)
register_batch_routes(app, limiter)

# ==========================================
# 🚀 Application Startup (Correct Order!)
# ==========================================

# 1. Initialize database FIRST (before any threads)
print("📦 Initializing database...")
init_db()

# 2. Handle pending jobs from previous session
if IS_HUGGINGFACE:
    # ✅ على HuggingFace: تنظيف بس المشlugل - مستني الباتشات تاني
    print("🔄 HuggingFace detected - cleaning stale single jobs...")
    try:
        stale_jobs = db_get_pending_jobs()
        for job in stale_jobs:
            # شيك لو الـ job ده مش جزء من batch
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT batch_id FROM batch_items WHERE job_id = ?", (job['id'],))
            batch_check = c.fetchone()
            conn.close()
            
            if batch_check is None:
                db_update_job(job['id'], status='error', error='Server restarted (HuggingFace sleep)')
            # batch jobs preserved
        
        if stale_jobs:
            print(f"🧹 Checked {len(stale_jobs)} stale jobs (batch jobs preserved)")
        
        # Reset running batches to pending
        stale_batches = db_get_pending_batches()
        for batch in stale_batches:
            if batch['status'] == 'running':
                db_update_batch(batch['id'], status='pending')
                print(f"  🔄 Reset batch {batch['id'][:8]}... to 'pending'")
    except Exception as e:
        print(f"⚠️ Failed to clean stale jobs: {e}")
else:
    print("🔄 Recovering pending jobs...")
    try:
        recover_pending_jobs()
    except Exception as e:
        print(f"⚠️ Failed to recover pending jobs: {e}")

    print("📦 Recovering pending batches...")
    try:
        recover_pending_batches()
    except Exception as e:
        print(f"⚠️ Failed to recover pending batches: {e}")

# 3. Start background threads AFTER database is ready
print("🧵 Starting background threads...")

batch_thread = threading.Thread(target=process_batch_queue, daemon=True, name="BatchProcessor")
batch_thread.start()
print("✅ Batch processor thread started")

cleanup_thread = threading.Thread(target=background_cleanup, daemon=True, name="CleanupThread")
cleanup_thread.start()
print("✅ Cleanup thread started")

print("🚀 Quran Reels Generator ready!")

if __name__ == "__main__":
    print("🚀 Starting Flask development server...")
    port = int(os.environ.get("PORT", "7860"))
    app.run(host='0.0.0.0', port=port, threaded=True)
