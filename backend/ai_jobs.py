#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OFITEC.AI - AI JOB MANAGEMENT
============================

Módulo para gestión de trabajos de IA y procesos asíncronos.
Extraído de server.py para mejor organización.
"""

from __future__ import annotations
import logging
import threading
import time
import traceback
from collections import defaultdict
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from config import get_prometheus_counter, get_prometheus_histogram
try:
    from prometheus_client import Gauge
    _METRICS_AVAILABLE = True
except ImportError:
    _METRICS_AVAILABLE = False
    
    class Gauge:  # type: ignore
        def __init__(self, *args, **kwargs): pass
        def inc(self, *args, **kwargs): pass
        def dec(self, *args, **kwargs): pass
        def set(self, *args, **kwargs): pass

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------------
# Job Status and State Management
# ----------------------------------------------------------------------------

class JobStatus(Enum):
    """Job execution status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class JobResult:
    """Container for job execution results."""
    job_id: str
    status: JobStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    progress: float = 0.0
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        data = asdict(self)
        data['status'] = self.status.value
        return data

    @property
    def duration(self) -> Optional[float]:
        """Calculate job duration if both timestamps are available."""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None


# ----------------------------------------------------------------------------
# Job Manager
# ----------------------------------------------------------------------------

class JobManager:
    """Thread-safe job management system."""

    def __init__(self):
        self._jobs: Dict[str, JobResult] = {}
        self._job_threads: Dict[str, threading.Thread] = {}
        self._lock = threading.Lock()
        self._progress_callbacks: Dict[str, List[Callable]] = defaultdict(list)
        
        # Metrics
        self._job_counter = get_prometheus_counter(
            'ai_jobs_total',
            'Total number of AI jobs processed',
            ['status', 'job_type']
        )
        self._job_duration = get_prometheus_histogram(
            'ai_job_duration_seconds',
            'Duration of AI job processing',
            ['job_type']
        )
        
        # Active jobs gauge
        if _METRICS_AVAILABLE:
            self._active_jobs_gauge = Gauge('ai_jobs_active', 'Current number of active AI jobs')
        else:
            self._active_jobs_gauge = Gauge()

    def _update_active_jobs_count(self):
        """Update the active jobs gauge with current count."""
        active_count = sum(1 for job in self._jobs.values()
                          if job.status == JobStatus.RUNNING)
        self._active_jobs_gauge.set(active_count)

    def create_job(self, job_id: str, metadata: Optional[Dict] = None) -> JobResult:
        """Create a new job with PENDING status."""
        with self._lock:
            if job_id in self._jobs:
                raise ValueError(f"Job {job_id} already exists")
            
            job = JobResult(
                job_id=job_id,
                status=JobStatus.PENDING,
                metadata=metadata or {}
            )
            self._jobs[job_id] = job
            return job

    def start_job(self,
                  job_id: str,
                  target_func: Callable,
                  args: tuple = (),
                  kwargs: Optional[Dict] = None) -> None:
        """Start job execution in a separate thread."""
        with self._lock:
            if job_id not in self._jobs:
                raise ValueError(f"Job {job_id} does not exist")
            
            job = self._jobs[job_id]
            if job.status != JobStatus.PENDING:
                raise ValueError(f"Job {job_id} is not in pending state")
            
            job.status = JobStatus.RUNNING
            self._update_active_jobs_count()
            job.started_at = time.time()
            
            # Create and start thread
            thread = threading.Thread(
                target=self._execute_job,
                args=(job_id, target_func, args, kwargs or {})
            )
            thread.daemon = True
            self._job_threads[job_id] = thread
            thread.start()

    def _execute_job(self,
                     job_id: str,
                     target_func: Callable,
                     args: tuple,
                     kwargs: Dict) -> None:
        """Execute job function and handle results/errors."""
        try:
            # Execute the function
            result = target_func(*args, **kwargs)
            
            with self._lock:
                job = self._jobs[job_id]
                job.status = JobStatus.COMPLETED
                job.result = result
                job.completed_at = time.time()
                job.progress = 1.0
                self._update_active_jobs_count()
                
                # Update metrics
                job_type = (job.metadata or {}).get('type', 'unknown')
                self._job_counter.labels(status='completed', job_type=job_type).inc()
                if job.duration:
                    self._job_duration.labels(job_type=job_type).observe(job.duration)
                
        except Exception as e:
            logger.error(f"Job {job_id} failed: {str(e)}")
            logger.error(traceback.format_exc())
            
            with self._lock:
                job = self._jobs[job_id]
                job.status = JobStatus.FAILED
                job.error = str(e)
                job.completed_at = time.time()
                self._update_active_jobs_count()
                
                # Update metrics
                job_type = (job.metadata or {}).get('type', 'unknown')
                self._job_counter.labels(status='failed', job_type=job_type).inc()
                
        finally:
            # Clean up thread reference
            with self._lock:
                self._job_threads.pop(job_id, None)

    def get_job(self, job_id: str) -> Optional[JobResult]:
        """Get job by ID."""
        with self._lock:
            return self._jobs.get(job_id)

    def get_all_jobs(self) -> List[JobResult]:
        """Get all jobs."""
        with self._lock:
            return list(self._jobs.values())

    def update_progress(self, job_id: str, progress: float) -> None:
        """Update job progress (0.0 to 1.0)."""
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].progress = max(0.0, min(1.0, progress))
                
                # Call progress callbacks
                for callback in self._progress_callbacks[job_id]:
                    try:
                        callback(job_id, progress)
                    except Exception as e:
                        logger.error(f"Progress callback error: {e}")

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a job if it's pending or running."""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return False
            
            if job.status in [JobStatus.PENDING, JobStatus.RUNNING]:
                job.status = JobStatus.CANCELLED
                job.completed_at = time.time()
                self._update_active_jobs_count()
                
                # Update metrics
                job_type = (job.metadata or {}).get('type', 'unknown')
                self._job_counter.labels(status='cancelled', job_type=job_type).inc()
                
                return True
            return False

    def cleanup_completed_jobs(self, max_age_seconds: float = 3600) -> int:
        """Remove old completed/failed/cancelled jobs."""
        cutoff_time = time.time() - max_age_seconds
        removed_count = 0
        
        with self._lock:
            to_remove = []
            for job_id, job in self._jobs.items():
                if (job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]
                        and job.completed_at
                        and job.completed_at < cutoff_time):
                    to_remove.append(job_id)
            
            for job_id in to_remove:
                self._jobs.pop(job_id, None)
                self._job_threads.pop(job_id, None)
                self._progress_callbacks.pop(job_id, None)
                removed_count += 1
        
        return removed_count

    def get_job_stats(self) -> Dict[str, Any]:
        """Get job manager statistics."""
        with self._lock:
            stats = {
                'total_jobs': len(self._jobs),
                'active_threads': len(self._job_threads),
                'status_counts': {}
            }
            
            # Count jobs by status
            for job in self._jobs.values():
                status = job.status.value
                stats['status_counts'][status] = stats['status_counts'].get(status, 0) + 1
            
            return stats


# ----------------------------------------------------------------------------
# Global Job Manager Instance
# ----------------------------------------------------------------------------

_job_manager: Optional[JobManager] = None
_manager_lock = threading.Lock()


def get_job_manager() -> JobManager:
    """Get the global job manager instance (singleton)."""
    global _job_manager
    
    if _job_manager is None:
        with _manager_lock:
            if _job_manager is None:
                _job_manager = JobManager()
    
    return _job_manager


def reset_job_manager():
    """Reset the global job manager - useful for testing."""
    global _job_manager
    with _manager_lock:
        _job_manager = None


# ----------------------------------------------------------------------------
# Convenience Functions
# ----------------------------------------------------------------------------

def create_ai_job(job_id: str,
                  job_type: str = "ai_task",
                  metadata: Optional[Dict] = None) -> JobResult:
    """Create a new AI job with standard metadata."""
    meta = metadata or {}
    meta['type'] = job_type
    meta['created_at'] = time.time()
    
    return get_job_manager().create_job(job_id, meta)


def run_ai_job(job_id: str,
               target_func: Callable,
               *args,
               **kwargs) -> None:
    """Start execution of an AI job."""
    get_job_manager().start_job(job_id, target_func, args, kwargs)


def get_ai_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """Get AI job status as dictionary."""
    job = get_job_manager().get_job(job_id)
    return job.to_dict() if job else None


def update_ai_job_progress(job_id: str, progress: float) -> None:
    """Update AI job progress."""
    get_job_manager().update_progress(job_id, progress)


def cleanup_old_jobs(max_age_hours: float = 1.0) -> int:
    """Clean up old completed jobs."""
    return get_job_manager().cleanup_completed_jobs(max_age_hours * 3600)

