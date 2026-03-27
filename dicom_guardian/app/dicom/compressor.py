"""DICOM compression utilities (Step 49)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from pydicom.uid import (
    DeflatedExplicitVRLittleEndian,
    ExplicitVRLittleEndian,
    UID,
)

from app.dicom.reader import read_dicom_file


SUPPORTED_COMPRESSION_MODES = {"none", "deflated"}


class CompressionError(Exception):
    """Raised when DICOM compression cannot be completed safely."""


@dataclass(frozen=True)
class CompressionPolicy:
    """Compression policy used by the processing pipeline."""

    mode: str
    overwrite: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CompressionResult:
    """Structured result for a compression operation."""

    mode: str
    source_file_path: str
    output_file_path: str
    source_transfer_syntax_uid: str
    output_transfer_syntax_uid: str
    source_size_bytes: int
    output_size_bytes: int
    bytes_delta: int
    was_compressed: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_compression_policy(
    *,
    mode: str = "deflated",
    overwrite: bool = False,
) -> CompressionPolicy:
    """Build and validate compression policy settings."""
    normalized_mode = str(mode).strip().lower()
    if normalized_mode not in SUPPORTED_COMPRESSION_MODES:
        raise CompressionError(
            f"unsupported compression mode: {normalized_mode}. "
            f"Supported modes: {sorted(SUPPORTED_COMPRESSION_MODES)}"
        )
    return CompressionPolicy(
        mode=normalized_mode,
        overwrite=bool(overwrite),
    )


def _resolve_path(file_path: str | Path) -> Path:
    resolved = Path(file_path).expanduser().resolve()
    if not resolved.exists():
        raise CompressionError(f"source DICOM file does not exist: {resolved}")
    if not resolved.is_file():
        raise CompressionError(f"source path is not a file: {resolved}")
    return resolved


def _resolve_output_path(
    source_file_path: Path,
    output_path: str | Path | None,
    *,
    overwrite: bool,
) -> Path:
    if overwrite and output_path is not None:
        raise CompressionError("overwrite and output_path are mutually exclusive")
    if overwrite:
        return source_file_path
    if output_path is not None:
        return Path(output_path).expanduser().resolve()
    return source_file_path.with_name(f"{source_file_path.stem}_compressed.dcm")


def _current_transfer_syntax_uid(dataset: Any) -> str:
    if getattr(dataset, "file_meta", None) is None:
        return ""
    return str(getattr(dataset.file_meta, "TransferSyntaxUID", "")).strip()


def _apply_deflated_transfer_syntax(dataset: Any) -> str:
    if getattr(dataset, "file_meta", None) is None:
        raise CompressionError("dataset is missing file_meta; cannot apply transfer syntax")
    dataset.file_meta.TransferSyntaxUID = UID(DeflatedExplicitVRLittleEndian)
    dataset.is_implicit_VR = False
    dataset.is_little_endian = True
    return str(dataset.file_meta.TransferSyntaxUID)


def _apply_passthrough_transfer_syntax(dataset: Any) -> str:
    if getattr(dataset, "file_meta", None) is None:
        raise CompressionError("dataset is missing file_meta; cannot preserve transfer syntax")
    current_uid = _current_transfer_syntax_uid(dataset)
    if not current_uid:
        dataset.file_meta.TransferSyntaxUID = UID(ExplicitVRLittleEndian)
        dataset.is_implicit_VR = False
        dataset.is_little_endian = True
        return str(dataset.file_meta.TransferSyntaxUID)
    return current_uid


def compress_dicom_file(
    file_path: str | Path,
    *,
    output_path: str | Path | None = None,
    policy: CompressionPolicy | None = None,
) -> CompressionResult:
    """Compress a DICOM file using the configured policy."""
    active_policy = policy or build_compression_policy()
    source = _resolve_path(file_path)
    destination = _resolve_output_path(
        source,
        output_path,
        overwrite=active_policy.overwrite,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)

    dataset = read_dicom_file(source, stop_before_pixels=False, force=False)
    source_transfer_syntax_uid = _current_transfer_syntax_uid(dataset)

    if active_policy.mode == "deflated":
        output_transfer_syntax_uid = _apply_deflated_transfer_syntax(dataset)
    elif active_policy.mode == "none":
        output_transfer_syntax_uid = _apply_passthrough_transfer_syntax(dataset)
    else:  # pragma: no cover - guarded by policy validation
        raise CompressionError(f"unsupported compression mode: {active_policy.mode}")

    dataset.save_as(str(destination), write_like_original=False)

    source_size = source.stat().st_size
    output_size = destination.stat().st_size

    return CompressionResult(
        mode=active_policy.mode,
        source_file_path=str(source),
        output_file_path=str(destination),
        source_transfer_syntax_uid=source_transfer_syntax_uid,
        output_transfer_syntax_uid=output_transfer_syntax_uid,
        source_size_bytes=source_size,
        output_size_bytes=output_size,
        bytes_delta=output_size - source_size,
        was_compressed=active_policy.mode != "none",
    )
