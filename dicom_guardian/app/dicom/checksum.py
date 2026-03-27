"""DICOM file checksum generation utilities (Step 36)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
from pathlib import Path
from typing import BinaryIO, Any


DEFAULT_CHUNK_SIZE = 1024 * 1024


class ChecksumError(Exception):
    """Raised when checksum generation cannot be completed safely."""


@dataclass(frozen=True)
class ChecksumResult:
    """Structured SHA256 checksum result for a file."""

    algorithm: str
    digest: str
    file_path: str
    file_size_bytes: int
    chunk_size_bytes: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ChecksumVerificationResult:
    """Structured result for SHA256 checksum verification."""

    algorithm: str
    file_path: str
    expected_digest: str
    actual_digest: str
    is_match: bool
    file_size_bytes: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CorruptionDetectionResult:
    """Structured result for file corruption detection."""

    algorithm: str
    file_path: str
    expected_digest: str
    actual_digest: str
    status: str
    is_corrupted: bool
    file_size_bytes: int
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _resolve_file_path(file_path: str | Path) -> Path:
    resolved = Path(file_path).expanduser().resolve()
    if not resolved.exists():
        raise ChecksumError(f"File does not exist: {resolved}")
    if not resolved.is_file():
        raise ChecksumError(f"Path is not a file: {resolved}")
    if resolved.stat().st_size <= 0:
        raise ChecksumError(f"File is empty: {resolved}")
    return resolved


def _validate_chunk_size(chunk_size: int) -> int:
    parsed = int(chunk_size)
    if parsed <= 0:
        raise ValueError("chunk_size must be greater than 0")
    return parsed


def _update_hash_from_stream(stream: BinaryIO, hasher: hashlib._Hash, chunk_size: int) -> None:
    while True:
        chunk = stream.read(chunk_size)
        if not chunk:
            break
        hasher.update(chunk)


def generate_file_checksum(
    file_path: str | Path,
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> ChecksumResult:
    """Generate a SHA256 checksum for a file using chunked reads."""
    resolved = _resolve_file_path(file_path)
    validated_chunk_size = _validate_chunk_size(chunk_size)
    hasher = hashlib.sha256()

    try:
        with resolved.open("rb") as handle:
            _update_hash_from_stream(handle, hasher, validated_chunk_size)
    except OSError as exc:
        raise ChecksumError(f"Unable to read file for checksum: {resolved}") from exc

    return ChecksumResult(
        algorithm="sha256",
        digest=hasher.hexdigest(),
        file_path=str(resolved),
        file_size_bytes=resolved.stat().st_size,
        chunk_size_bytes=validated_chunk_size,
    )


def generate_sha256(file_path: str | Path, *, chunk_size: int = DEFAULT_CHUNK_SIZE) -> str:
    """Return only the SHA256 digest string for a file."""
    return generate_file_checksum(file_path, chunk_size=chunk_size).digest


def verify_file_checksum(
    file_path: str | Path,
    expected_digest: str,
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> ChecksumVerificationResult:
    """Verify a file against an expected SHA256 digest."""
    normalized_expected = str(expected_digest).strip().lower()
    if len(normalized_expected) != 64:
        raise ValueError("expected_digest must be a 64-character SHA256 hex digest")

    actual = generate_file_checksum(file_path, chunk_size=chunk_size)
    return ChecksumVerificationResult(
        algorithm=actual.algorithm,
        file_path=actual.file_path,
        expected_digest=normalized_expected,
        actual_digest=actual.digest,
        is_match=actual.digest == normalized_expected,
        file_size_bytes=actual.file_size_bytes,
    )


def detect_file_corruption(
    file_path: str | Path,
    expected_digest: str,
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> CorruptionDetectionResult:
    """Detect whether a file has been corrupted relative to a stored SHA256 digest."""
    verification = verify_file_checksum(
        file_path=file_path,
        expected_digest=expected_digest,
        chunk_size=chunk_size,
    )
    is_corrupted = not verification.is_match
    return CorruptionDetectionResult(
        algorithm=verification.algorithm,
        file_path=verification.file_path,
        expected_digest=verification.expected_digest,
        actual_digest=verification.actual_digest,
        status="CORRUPTED" if is_corrupted else "HEALTHY",
        is_corrupted=is_corrupted,
        file_size_bytes=verification.file_size_bytes,
        reason="checksum mismatch detected" if is_corrupted else "checksum verification passed",
    )
