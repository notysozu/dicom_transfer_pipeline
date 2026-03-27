"""Basic DICOM file reader utilities (Step 31)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pydicom
from pydicom.dataset import FileDataset


class DicomReadError(Exception):
    """Raised when a DICOM file cannot be safely loaded."""


def _resolve_file_path(file_path: str | Path) -> Path:
    resolved = Path(file_path).expanduser().resolve()
    if not resolved.exists():
        raise DicomReadError(f"DICOM file does not exist: {resolved}")
    if not resolved.is_file():
        raise DicomReadError(f"DICOM path is not a file: {resolved}")
    if resolved.stat().st_size <= 0:
        raise DicomReadError(f"DICOM file is empty: {resolved}")
    return resolved


def read_dicom_file(
    file_path: str | Path,
    *,
    stop_before_pixels: bool = True,
    force: bool = False,
) -> FileDataset:
    """Read and return a DICOM dataset from disk.

    Parameters:
    - `stop_before_pixels`: avoids loading pixel data for lightweight reads.
    - `force`: allows reading malformed DICOMs when explicitly requested.
    """
    resolved = _resolve_file_path(file_path)

    try:
        dataset = pydicom.dcmread(
            str(resolved),
            stop_before_pixels=stop_before_pixels,
            force=force,
        )
    except Exception as exc:  # pragma: no cover - exact pydicom exception varies
        raise DicomReadError(f"Failed to read DICOM file {resolved}: {exc}") from exc

    return dataset


def dataset_summary(dataset: FileDataset) -> dict[str, Any]:
    """Return a minimal summary from the loaded dataset."""
    return {
        "sop_instance_uid": str(getattr(dataset, "SOPInstanceUID", "")),
        "study_instance_uid": str(getattr(dataset, "StudyInstanceUID", "")),
        "series_instance_uid": str(getattr(dataset, "SeriesInstanceUID", "")),
        "modality": str(getattr(dataset, "Modality", "")),
        "patient_id": str(getattr(dataset, "PatientID", "")),
        "has_pixel_data": bool(getattr(dataset, "PixelData", None)),
    }
