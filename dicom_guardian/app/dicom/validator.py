"""DICOM metadata extraction and validation utilities (Steps 32-33)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re
from datetime import datetime
from shutil import move
from typing import Any
from uuid import uuid4

from pydicom.dataset import FileDataset

from app.dicom.reader import read_dicom_file


@dataclass(frozen=True)
class DicomMetadata:
    """Core metadata fields extracted from a DICOM dataset."""

    study_instance_uid: str
    series_instance_uid: str
    sop_instance_uid: str
    patient_id: str
    patient_name: str
    accession_number: str
    modality: str
    study_date: str
    study_time: str
    instance_number: int | None
    sop_class_uid: str
    transfer_syntax_uid: str
    source_file_path: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MetadataValidationResult:
    """Validation result for extracted DICOM metadata."""

    is_valid: bool
    errors: list[str]
    warnings: list[str]
    metadata: DicomMetadata

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "metadata": self.metadata.to_dict(),
        }


@dataclass(frozen=True)
class RejectionResult:
    """Represents the outcome of an invalid study rejection workflow."""

    transfer_uid: str
    source_file_path: str
    rejection_file_path: str
    reason: str
    errors: list[str]
    warnings: list[str]
    db_record: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "transfer_uid": self.transfer_uid,
            "source_file_path": self.source_file_path,
            "rejection_file_path": self.rejection_file_path,
            "reason": self.reason,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "db_record": dict(self.db_record),
        }


UID_PATTERN = re.compile(r"^[0-9]+(\.[0-9]+)+$")
DATE_PATTERN = re.compile(r"^\d{8}$")
TIME_PATTERN = re.compile(r"^\d{2}(\d{2}(\d{2}(\.\d{1,6})?)?)?$")
ALLOWED_MODALITIES = {
    "CR",
    "CT",
    "DX",
    "MG",
    "MR",
    "NM",
    "OT",
    "PT",
    "RF",
    "SC",
    "US",
    "XA",
}


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _safe_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def extract_metadata_from_dataset(
    dataset: FileDataset,
    *,
    source_file_path: str | Path = "",
) -> DicomMetadata:
    """Extract key metadata from a loaded DICOM dataset."""
    transfer_syntax_uid = ""
    if getattr(dataset, "file_meta", None) is not None:
        transfer_syntax_uid = _safe_str(getattr(dataset.file_meta, "TransferSyntaxUID", ""))

    return DicomMetadata(
        study_instance_uid=_safe_str(getattr(dataset, "StudyInstanceUID", "")),
        series_instance_uid=_safe_str(getattr(dataset, "SeriesInstanceUID", "")),
        sop_instance_uid=_safe_str(getattr(dataset, "SOPInstanceUID", "")),
        patient_id=_safe_str(getattr(dataset, "PatientID", "")),
        patient_name=_safe_str(getattr(dataset, "PatientName", "")),
        accession_number=_safe_str(getattr(dataset, "AccessionNumber", "")),
        modality=_safe_str(getattr(dataset, "Modality", "")),
        study_date=_safe_str(getattr(dataset, "StudyDate", "")),
        study_time=_safe_str(getattr(dataset, "StudyTime", "")),
        instance_number=_safe_int(getattr(dataset, "InstanceNumber", None)),
        sop_class_uid=_safe_str(getattr(dataset, "SOPClassUID", "")),
        transfer_syntax_uid=transfer_syntax_uid,
        source_file_path=str(source_file_path),
    )


def extract_metadata_from_file(file_path: str | Path) -> DicomMetadata:
    """Read a DICOM file and extract core metadata fields."""
    resolved = Path(file_path).expanduser().resolve()
    dataset = read_dicom_file(resolved, stop_before_pixels=True, force=False)
    return extract_metadata_from_dataset(dataset, source_file_path=resolved)


def _validate_required_fields(metadata: DicomMetadata, errors: list[str]) -> None:
    required = {
        "study_instance_uid": metadata.study_instance_uid,
        "series_instance_uid": metadata.series_instance_uid,
        "sop_instance_uid": metadata.sop_instance_uid,
        "patient_id": metadata.patient_id,
        "modality": metadata.modality,
        "sop_class_uid": metadata.sop_class_uid,
        "transfer_syntax_uid": metadata.transfer_syntax_uid,
    }
    for field_name, value in required.items():
        if not value:
            errors.append(f"{field_name} is required")


def _validate_uid(field_name: str, value: str, errors: list[str]) -> None:
    if value and not UID_PATTERN.match(value):
        errors.append(f"{field_name} is not a valid DICOM UID")


def _validate_date(value: str, errors: list[str]) -> None:
    if value and not DATE_PATTERN.match(value):
        errors.append("study_date must be in YYYYMMDD format")


def _validate_time(value: str, errors: list[str]) -> None:
    if value and not TIME_PATTERN.match(value):
        errors.append("study_time must be in HHMMSS[.ffffff] format")


def _validate_modality(value: str, warnings: list[str]) -> None:
    if value and value.upper() not in ALLOWED_MODALITIES:
        warnings.append(f"modality '{value}' is uncommon or unsupported by policy")


def _validate_instance_number(value: int | None, errors: list[str]) -> None:
    if value is not None and value <= 0:
        errors.append("instance_number must be greater than 0 when present")


def validate_metadata(metadata: DicomMetadata) -> MetadataValidationResult:
    """Validate extracted metadata against baseline DICOM policy rules."""
    errors: list[str] = []
    warnings: list[str] = []

    _validate_required_fields(metadata, errors)
    _validate_uid("study_instance_uid", metadata.study_instance_uid, errors)
    _validate_uid("series_instance_uid", metadata.series_instance_uid, errors)
    _validate_uid("sop_instance_uid", metadata.sop_instance_uid, errors)
    _validate_uid("sop_class_uid", metadata.sop_class_uid, errors)
    _validate_uid("transfer_syntax_uid", metadata.transfer_syntax_uid, errors)

    _validate_date(metadata.study_date, errors)
    _validate_time(metadata.study_time, errors)
    _validate_modality(metadata.modality, warnings)
    _validate_instance_number(metadata.instance_number, errors)

    if not metadata.patient_name:
        warnings.append("patient_name is empty")
    if not metadata.accession_number:
        warnings.append("accession_number is empty")

    return MetadataValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        metadata=metadata,
    )


def validate_metadata_from_file(file_path: str | Path) -> MetadataValidationResult:
    """Read a DICOM file, extract metadata, and validate it."""
    metadata = extract_metadata_from_file(file_path)
    return validate_metadata(metadata)


def reject_invalid_study(
    file_path: str | Path,
    validation_result: MetadataValidationResult,
    *,
    rejection_root: str | Path = "data/rejected",
) -> RejectionResult:
    """Reject invalid DICOM file by quarantining and recording failure."""
    from app.database.db import record_rejected_transfer

    if validation_result.is_valid:
        raise ValueError("reject_invalid_study called with a valid validation result")

    source = Path(file_path).expanduser().resolve()
    if not source.exists() or not source.is_file():
        raise FileNotFoundError(f"Source file not found for rejection: {source}")

    rejected_base = Path(rejection_root).expanduser().resolve()
    day_folder = datetime.utcnow().strftime("%Y%m%d")
    target_dir = rejected_base / day_folder
    target_dir.mkdir(parents=True, exist_ok=True)

    transfer_uid = f"reject-{uuid4().hex}"
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    target_name = f"{timestamp}_{transfer_uid}_{source.name}"
    target_path = target_dir / target_name

    move(str(source), str(target_path))

    reason = "; ".join(validation_result.errors) if validation_result.errors else "metadata validation failed"
    record = record_rejected_transfer(
        transfer_uid=transfer_uid,
        source_file_path=str(source),
        rejection_file_path=str(target_path),
        failure_reason=reason,
        study_instance_uid=validation_result.metadata.study_instance_uid,
        sop_instance_uid=validation_result.metadata.sop_instance_uid or None,
    )

    return RejectionResult(
        transfer_uid=transfer_uid,
        source_file_path=str(source),
        rejection_file_path=str(target_path),
        reason=reason,
        errors=list(validation_result.errors),
        warnings=list(validation_result.warnings),
        db_record=record,
    )
