"""Asynchronous processing queue utilities (Step 46)."""

from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from shutil import copy2
from typing import Any, Awaitable, Callable
from uuid import uuid4


class PipelineQueueError(Exception):
    """Raised when the processing queue encounters an invalid operation."""


@dataclass(frozen=True)
class ProcessingJob:
    """Single inbound processing job queued for downstream pipeline work."""

    job_id: str
    transfer_uid: str
    study_instance_uid: str
    sop_instance_uid: str
    file_path: str
    stage: str = "RECEIVED"
    retry_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    enqueued_at: str = field(default_factory=lambda: datetime.utcnow().isoformat(timespec="seconds") + "Z")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class QueueSnapshot:
    """Observable queue state snapshot for monitoring and diagnostics."""

    queue_size: int
    is_running: bool
    maxsize: int
    processed_jobs: int
    failed_jobs: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ValidationPipelineResult:
    """Structured result for the metadata validation pipeline stage."""

    job: ProcessingJob
    status: str
    transfer_record: dict[str, Any]
    validation: dict[str, Any]
    rejection: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "job": self.job.to_dict(),
            "status": self.status,
            "transfer_record": dict(self.transfer_record),
            "validation": dict(self.validation),
            "rejection": None if self.rejection is None else dict(self.rejection),
        }


@dataclass(frozen=True)
class ChecksumPipelineResult:
    """Structured result for the checksum pipeline stage."""

    job: ProcessingJob
    status: str
    transfer_record: dict[str, Any]
    checksum: dict[str, Any]
    instance_metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "job": self.job.to_dict(),
            "status": self.status,
            "transfer_record": dict(self.transfer_record),
            "checksum": dict(self.checksum),
            "instance_metadata": dict(self.instance_metadata),
        }


@dataclass(frozen=True)
class ProcessedOutputResult:
    """Structured result for the processed-output pipeline stage."""

    job: ProcessingJob
    status: str
    processed_file_path: str
    transfer_record: dict[str, Any]
    instance_metadata: dict[str, Any]
    compression: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "job": self.job.to_dict(),
            "status": self.status,
            "processed_file_path": self.processed_file_path,
            "transfer_record": dict(self.transfer_record),
            "instance_metadata": dict(self.instance_metadata),
            "compression": dict(self.compression),
        }


def create_processing_job(
    *,
    transfer_uid: str,
    study_instance_uid: str,
    sop_instance_uid: str,
    file_path: str | Path,
    stage: str = "RECEIVED",
    retry_count: int = 0,
    metadata: dict[str, Any] | None = None,
    job_id: str | None = None,
) -> ProcessingJob:
    """Create a validated processing job for the async queue."""
    normalized_transfer_uid = str(transfer_uid).strip()
    normalized_study_uid = str(study_instance_uid).strip()
    normalized_sop_uid = str(sop_instance_uid).strip()
    normalized_file_path = str(Path(file_path).expanduser().resolve()).strip()
    normalized_stage = str(stage).strip().upper()

    if not normalized_transfer_uid:
        raise PipelineQueueError("transfer_uid is required")
    if not normalized_study_uid:
        raise PipelineQueueError("study_instance_uid is required")
    if not normalized_sop_uid:
        raise PipelineQueueError("sop_instance_uid is required")
    if not normalized_file_path:
        raise PipelineQueueError("file_path is required")
    if retry_count < 0:
        raise PipelineQueueError("retry_count must be >= 0")

    return ProcessingJob(
        job_id=job_id or f"job-{uuid4().hex}",
        transfer_uid=normalized_transfer_uid,
        study_instance_uid=normalized_study_uid,
        sop_instance_uid=normalized_sop_uid,
        file_path=normalized_file_path,
        stage=normalized_stage or "RECEIVED",
        retry_count=int(retry_count),
        metadata=dict(metadata or {}),
    )


class AsyncProcessingQueue:
    """In-memory asyncio queue for serialized downstream DICOM processing."""

    def __init__(self, *, maxsize: int = 0) -> None:
        if int(maxsize) < 0:
            raise PipelineQueueError("maxsize must be >= 0")
        self._queue: asyncio.Queue[ProcessingJob] = asyncio.Queue(maxsize=int(maxsize))
        self._running = False
        self._processed_jobs = 0
        self._failed_jobs = 0

    @property
    def is_running(self) -> bool:
        return self._running

    async def enqueue(self, job: ProcessingJob) -> None:
        """Put a processing job onto the queue."""
        if not isinstance(job, ProcessingJob):
            raise PipelineQueueError("job must be a ProcessingJob instance")
        await self._queue.put(job)

    async def dequeue(self) -> ProcessingJob:
        """Remove and return the next queued processing job."""
        return await self._queue.get()

    def task_done(self) -> None:
        """Mark the last dequeued item as processed."""
        self._queue.task_done()

    async def join(self) -> None:
        """Block until all queued jobs are processed."""
        await self._queue.join()

    def snapshot(self) -> QueueSnapshot:
        """Return a monitoring-friendly snapshot of queue state."""
        return QueueSnapshot(
            queue_size=self._queue.qsize(),
            is_running=self._running,
            maxsize=self._queue.maxsize,
            processed_jobs=self._processed_jobs,
            failed_jobs=self._failed_jobs,
        )

    async def run_worker(
        self,
        processor: Callable[[ProcessingJob], Awaitable[Any]],
        *,
        stop_when_empty: bool = False,
    ) -> None:
        """Run a worker loop that processes jobs using the supplied async handler."""
        if self._running:
            raise PipelineQueueError("queue worker is already running")

        self._running = True
        try:
            while True:
                if stop_when_empty and self._queue.empty():
                    break

                job = await self.dequeue()
                try:
                    await processor(job)
                    self._processed_jobs += 1
                except Exception:
                    self._failed_jobs += 1
                    raise
                finally:
                    self.task_done()
        finally:
            self._running = False


def build_enqueue_callback(
    queue: AsyncProcessingQueue,
    *,
    transfer_uid_getter: Callable[[Any], str] | None = None,
) -> Callable[[Any], Awaitable[ProcessingJob]]:
    """Build an async callback that converts inbound objects into queued processing jobs."""

    async def enqueue_result(result: Any) -> ProcessingJob:
        transfer_uid = ""
        if transfer_uid_getter is not None:
            transfer_uid = str(transfer_uid_getter(result)).strip()
        elif hasattr(result, "transfer_uid"):
            transfer_uid = str(getattr(result, "transfer_uid")).strip()
        elif isinstance(result, dict):
            transfer_uid = str(result.get("transfer_uid", "")).strip()

        if not transfer_uid:
            raise PipelineQueueError("unable to derive transfer_uid for queued processing job")

        if hasattr(result, "incoming_storage"):
            incoming_storage = getattr(result, "incoming_storage")
            job = create_processing_job(
                transfer_uid=transfer_uid,
                study_instance_uid=str(getattr(incoming_storage, "study_instance_uid")).strip(),
                sop_instance_uid=str(getattr(incoming_storage, "sop_instance_uid")).strip(),
                file_path=str(getattr(incoming_storage, "file_path")).strip(),
                metadata={"source": type(result).__name__},
            )
        elif isinstance(result, dict):
            job = create_processing_job(
                transfer_uid=transfer_uid,
                study_instance_uid=str(result["study_instance_uid"]).strip(),
                sop_instance_uid=str(result["sop_instance_uid"]).strip(),
                file_path=str(result["file_path"]).strip(),
                metadata={"source": "dict"},
            )
        else:
            raise PipelineQueueError("unsupported result type for enqueue callback")

        await queue.enqueue(job)
        return job

    return enqueue_result


async def validate_processing_job(
    job: ProcessingJob,
    *,
    db_path: str | Path | None = None,
    reject_invalid: bool = True,
    rejection_root: str | Path = "data/rejected",
) -> ValidationPipelineResult:
    """Validate a queued DICOM job and update persistence state accordingly."""
    from app.database.db import get_transfer_by_uid, update_transfer_status
    from app.dicom.validator import reject_invalid_study, validate_metadata_from_file

    validation_result = validate_metadata_from_file(job.file_path)
    transfer_record = get_transfer_by_uid(job.transfer_uid, db_path=db_path)
    if transfer_record is None:
        raise PipelineQueueError(f"transfer_uid not found for validation job: {job.transfer_uid}")

    if validation_result.is_valid:
        updated_transfer = update_transfer_status(
            transfer_uid=job.transfer_uid,
            status="VALIDATED",
            failure_reason=None,
            db_path=db_path,
        )
        return ValidationPipelineResult(
            job=job,
            status="VALIDATED",
            transfer_record=updated_transfer,
            validation=validation_result.to_dict(),
            rejection=None,
        )

    failure_reason = "; ".join(validation_result.errors) if validation_result.errors else "metadata validation failed"
    updated_transfer = update_transfer_status(
        transfer_uid=job.transfer_uid,
        status="FAILED",
        failure_reason=failure_reason,
        db_path=db_path,
    )

    rejection_payload: dict[str, Any] | None = None
    if reject_invalid:
        rejection = reject_invalid_study(
            job.file_path,
            validation_result,
            rejection_root=rejection_root,
        )
        rejection_payload = rejection.to_dict()

    return ValidationPipelineResult(
        job=job,
        status="FAILED",
        transfer_record=updated_transfer,
        validation=validation_result.to_dict(),
        rejection=rejection_payload,
    )


async def checksum_processing_job(
    job: ProcessingJob,
    *,
    db_path: str | Path | None = None,
    next_status: str = "QUEUED",
) -> ChecksumPipelineResult:
    """Generate and persist a SHA256 checksum for a validated processing job."""
    from app.database.db import (
        get_transfer_by_uid,
        store_instance_checksum,
        update_transfer_status,
    )
    from app.dicom.checksum import generate_file_checksum

    transfer_record = get_transfer_by_uid(job.transfer_uid, db_path=db_path)
    if transfer_record is None:
        raise PipelineQueueError(f"transfer_uid not found for checksum job: {job.transfer_uid}")

    checksum_result = generate_file_checksum(job.file_path)
    instance_metadata = store_instance_checksum(
        sop_instance_uid=job.sop_instance_uid,
        checksum_sha256=checksum_result.digest,
        db_path=db_path,
    )
    updated_transfer = update_transfer_status(
        transfer_uid=job.transfer_uid,
        status=next_status,
        failure_reason=None,
        db_path=db_path,
    )

    return ChecksumPipelineResult(
        job=job,
        status=str(next_status).strip().upper(),
        transfer_record=updated_transfer,
        checksum=checksum_result.to_dict(),
        instance_metadata=instance_metadata,
    )


def build_processed_output_path(
    *,
    file_path: str | Path,
    study_instance_uid: str,
    sop_instance_uid: str,
    processed_root: str | Path = "data/processed",
) -> Path:
    """Build the destination path for a processed DICOM output artifact."""
    source = Path(file_path).expanduser().resolve()
    root = Path(processed_root).expanduser().resolve()
    day_folder = datetime.utcnow().strftime("%Y%m%d")
    study_folder = str(study_instance_uid).strip() or "unknown-study"
    sop_uid = str(sop_instance_uid).strip() or source.stem or f"unknown-instance-{uuid4().hex}"
    target_dir = root / day_folder / study_folder
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir / f"{sop_uid}.dcm"


async def produce_processed_output(
    job: ProcessingJob,
    *,
    db_path: str | Path | None = None,
    processed_root: str | Path = "data/processed",
    compression_mode: str = "deflated",
    preserve_incoming_copy: bool = True,
) -> ProcessedOutputResult:
    """Write a processed DICOM artifact under data/processed and update instance metadata."""
    from app.database.db import (
        get_instance_by_sop_uid,
        get_transfer_by_uid,
        upsert_instance_metadata,
        update_transfer_status,
    )
    from app.dicom.compressor import build_compression_policy, compress_dicom_file

    transfer_record = get_transfer_by_uid(job.transfer_uid, db_path=db_path)
    if transfer_record is None:
        raise PipelineQueueError(f"transfer_uid not found for processed output job: {job.transfer_uid}")

    instance_record = get_instance_by_sop_uid(job.sop_instance_uid, db_path=db_path)
    if instance_record is None:
        raise PipelineQueueError(f"sop_instance_uid not found for processed output job: {job.sop_instance_uid}")

    output_path = build_processed_output_path(
        file_path=job.file_path,
        study_instance_uid=job.study_instance_uid,
        sop_instance_uid=job.sop_instance_uid,
        processed_root=processed_root,
    )

    policy = build_compression_policy(mode=compression_mode, overwrite=False)
    compression_result = compress_dicom_file(
        job.file_path,
        output_path=output_path,
        policy=policy,
    )

    if preserve_incoming_copy and Path(job.file_path).expanduser().resolve() == Path(compression_result.output_file_path):
        copied_output = output_path
        copied_output.parent.mkdir(parents=True, exist_ok=True)
        copy2(job.file_path, copied_output)
        processed_file_path = str(copied_output)
        compression_payload = {
            **compression_result.to_dict(),
            "output_file_path": processed_file_path,
        }
    else:
        processed_file_path = compression_result.output_file_path
        compression_payload = compression_result.to_dict()

    instance_metadata = upsert_instance_metadata(
        {
            "study_instance_uid": instance_record["study_instance_uid"],
            "sop_instance_uid": instance_record["sop_instance_uid"],
            "series_instance_uid": instance_record.get("series_instance_uid"),
            "sop_class_uid": instance_record.get("sop_class_uid"),
            "instance_number": instance_record.get("instance_number"),
            "transfer_syntax_uid": compression_payload["output_transfer_syntax_uid"],
            "file_path": processed_file_path,
            "checksum_sha256": instance_record.get("checksum_sha256"),
        },
        db_path=db_path,
    )

    updated_transfer = update_transfer_status(
        transfer_uid=job.transfer_uid,
        status="QUEUED",
        failure_reason=None,
        db_path=db_path,
    )

    return ProcessedOutputResult(
        job=job,
        status="QUEUED",
        processed_file_path=processed_file_path,
        transfer_record=updated_transfer,
        instance_metadata=instance_metadata,
        compression=compression_payload,
    )
