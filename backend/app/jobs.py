"""Background jobs for the Monte Carlo, and nothing else.

A Monte Carlo run re-runs the whole fit thousands of times and takes tens of
seconds to minutes. Doing that inside the request would hold the connection open
with nothing to show, which FR-018 forbids. So the request starts a thread,
registers a job, and returns an identifier immediately; the client polls.

A thread rather than a process, because the work sits inside NumPy and SciPy,
which release the interpreter lock. A dictionary rather than a queue system,
because the application is single-user and single-container and loses nothing by
forgetting jobs on restart (plan.md section 5).

This module is the one component to replace if either assumption ever stops
holding, which is why it is small and isolated.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field

from .core.errors import CoreError, JobNotFound
from .core.montecarlo import propagate
from .core.types import (
    AnalysisSettings,
    JobState,
    MeasurementDataset,
    UncertaintyResult,
    UncertaintySettings,
)

#: Jobs older than this many completed entries are discarded oldest-first, so a
#: long-lived process cannot grow without bound. Generous: each result is a few
#: hundred bytes.
MAX_RETAINED = 64


@dataclass
class Job:
    job_id: str
    state: JobState = JobState.PENDING
    progress: float = 0.0
    result: UncertaintyResult | None = None
    error: dict | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def snapshot(self) -> "Job":
        """A consistent copy, so a poll never observes a half-written update."""
        with self._lock:
            return Job(
                job_id=self.job_id,
                state=self.state,
                progress=self.progress,
                result=self.result,
                error=self.error,
            )


class JobStore:
    """In-process job registry. Safe to call from several threads."""

    def __init__(self, max_retained: int = MAX_RETAINED) -> None:
        self._jobs: dict[str, Job] = {}
        self._order: list[str] = []
        self._lock = threading.Lock()
        self._max_retained = max_retained

    def get(self, job_id: str) -> Job:
        with self._lock:
            job = self._jobs.get(job_id)
        if job is None:
            raise JobNotFound(job_id=job_id)
        return job.snapshot()

    def _register(self) -> Job:
        job = Job(job_id=uuid.uuid4().hex)
        with self._lock:
            self._jobs[job.job_id] = job
            self._order.append(job.job_id)
            while len(self._order) > self._max_retained:
                stale = self._order.pop(0)
                self._jobs.pop(stale, None)
        return job

    def submit(
        self,
        dataset: MeasurementDataset,
        settings: AnalysisSettings,
        uncertainty: UncertaintySettings,
    ) -> str:
        """Start a Monte Carlo run and return its identifier immediately."""
        job = self._register()

        def report(fraction: float) -> None:
            with job._lock:
                job.progress = float(fraction)

        def run() -> None:
            with job._lock:
                job.state = JobState.RUNNING
            try:
                result = propagate(dataset, settings, uncertainty, progress=report)
            except CoreError as exc:
                with job._lock:
                    job.state = JobState.FAILED
                    job.error = exc.payload()
                return
            except Exception as exc:                      # noqa: BLE001
                # An unexpected failure must still reach the user as a code
                # rather than as a job that never finishes (constitution IV).
                with job._lock:
                    job.state = JobState.FAILED
                    job.error = {"code": "INTERNAL", "params": {"detail": str(exc)}}
                return
            with job._lock:
                job.result = result
                job.progress = 1.0
                job.state = JobState.SUCCEEDED

        threading.Thread(target=run, name=f"mc-{job.job_id[:8]}", daemon=True).start()
        return job.job_id


#: The single store the API uses. Module-level because the process is the scope.
store = JobStore()
