"""
Job management — in-memory JOBS dict, create/update/get helpers, progress logger.
"""
import os
import uuid
import time
import datetime
import threading
from proglog import ProgressBarLogger
from config import BASE_TEMP_DIR
from database import db_create_job, db_update_job, db_get_job

# ==========================================
# 🧠 Job Management (RAM + SQLite for Persistence)
# ==========================================
JOBS = {}  # RAM cache for fast access
JOBS_LOCK = threading.Lock()

def create_job(config=None, session_id=None):
    """Create a new job - stores in RAM and SQLite with session support"""
    job_id = str(uuid.uuid4())
    job_dir = os.path.join(BASE_TEMP_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)
    
    # Store in RAM for fast access
    with JOBS_LOCK:
        JOBS[job_id] = {
            'id': job_id, 
            'percent': 0, 
            'status': 'pending', 
            'eta': '--:--', 
            'is_running': True, 
            'is_complete': False, 
            'output_path': None, 
            'error': None, 
            'should_stop': False, 
            'created_at': time.time(), 
            'workspace': job_dir,
            'session_id': session_id,
            'background_source_used': 'unknown',
            'background_fetch_error': None
        }
    
    # Store in SQLite for persistence
    db_create_job(job_id, job_dir, config, session_id)
    
    return job_id

def update_job_status(job_id, percent, status, eta=None):
    """Update job status - RAM + SQLite"""
    with JOBS_LOCK:
        if job_id in JOBS:
            JOBS[job_id]['percent'] = percent
            JOBS[job_id]['status'] = status
            if eta: JOBS[job_id]['eta'] = eta
    
    # Update in SQLite ( throttled - every 5% or on completion)
    if percent % 5 == 0 or percent >= 100 or 'complete' in status.lower() or 'error' in status.lower():
        db_data = {'percent': percent, 'status': status}
        if eta:
            db_data['eta'] = eta
        db_update_job(job_id, **db_data)

def update_job_metadata(job_id, **kwargs):
    """Update lightweight in-memory metadata fields for diagnostics."""
    with JOBS_LOCK:
        if job_id in JOBS:
            JOBS[job_id].update(kwargs)

def get_job(job_id):
    """Get job - try RAM first, then SQLite"""
    with JOBS_LOCK:
        if job_id in JOBS:
            return JOBS[job_id]
    
    # Not in RAM, try SQLite
    db_job = db_get_job(job_id)
    if db_job:
        # Reconstruct job dict for compatibility
        return {
            'id': db_job['id'],
            'percent': db_job['percent'],
            'status': db_job['status'],
            'eta': db_job['eta'],
            'is_running': db_job['status'] in ('pending', 'processing'),
            'is_complete': db_job['status'] == 'complete',
            'output_path': db_job['output_path'],
            'error': db_job['error'],
            'should_stop': bool(db_job['should_stop']),
            'created_at': db_job['created_at'],
            'workspace': db_job['workspace'],
            'background_source_used': db_job.get('background_source_used', 'unknown') if isinstance(db_job, dict) else 'unknown',
            'background_fetch_error': db_job.get('background_fetch_error') if isinstance(db_job, dict) else None
        }
    return None

def check_stop(job_id):
    """Check if job should stop"""
    job = get_job(job_id)
    if not job:
        # Job not found in RAM or SQLite - might have been cleaned up
        print(f"[WARNING] Job {job_id} not found in check_stop - assuming completed or cleaned up")
        return
    if job.get('should_stop', False):
        raise Exception("Stopped by user")

def cleanup_job(job_id):
    """Remove job from RAM (keep in SQLite for history)"""
    with JOBS_LOCK:
        job = JOBS.pop(job_id, None)
    # Don't delete files - keep them for download
    # Files will be cleaned up by background_cleanup after 12h

class ScopedQuranLogger(ProgressBarLogger):
    def __init__(self, job_id):
        super().__init__()
        self.job_id = job_id
        self.start_time = None

    def bars_callback(self, bar, attr, value, old_value=None):
        if bar == 't':
            check_stop(self.job_id)
            total = self.bars[bar]['total']
            if total > 0:
                percent = int((value / total) * 100)
                if self.start_time is None: self.start_time = time.time()
                elapsed = time.time() - self.start_time
                rem_str = "00:00"
                if elapsed > 0 and value > 0:
                    rate = value / elapsed
                    remaining = (total - value) / rate
                    rem_str = str(datetime.timedelta(seconds=int(remaining)))[2:] if remaining > 0 else "00:00"
                update_job_status(self.job_id, percent, f"جاري التصدير... {percent}%", eta=rem_str)
