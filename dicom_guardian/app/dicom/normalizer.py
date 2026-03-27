"""DICOM metadata normalization utilities (Step 35)."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from pydicom.dataset import FileDataset

from app.dicom.reader import read_dicom_file


@dataclass(frozen=True)
class NormalizationChange:
    """Single normalization change made to a DICOM attribute."""

    field: str
    before: str
    after: str
    reason: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class NormalizationResult:
    """Result payload from DICOM normalization."""

    was_modified: bool
    changes: list[NormalizationChange]
    warnings: list[str]
    normalized_dataset: FileDataset

    def to_dict(self) -> dict[str, Any]:
        return {
            "was_modified": self.was_modified,
            "changes": [item.to_dict() for item in self.changes],
            "warnings": list(self.warnings),
            "study_instance_uid": str(getattr(self.normalized_dataset, "StudyInstanceUID", "")),
            "series_instance_uid": str(getattr(self.normalized_dataset, "SeriesInstanceUID", "")),
            "sop_instance_uid": str(getattr(self.normalized_dataset, "SOPInstanceUID", "")),
        }


def _clean(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _record_change(
    *,
    dataset: FileDataset,
    field: str,
    current: Any,
    normalized: str,
    reason: str,
    changes: list[NormalizationChange],
) -> None:
    before = _clean(current)
    if before == normalized:
        return
    setattr(dataset, field, normalized)
    changes.append(
        NormalizationChange(
            field=field,
            before=before,
            after=normalized,
            reason=reason,
        )
    )


def _normalize_person_name(value: Any) -> str:
    raw = _clean(value)
    if not raw:
        return raw
    return "^".join(part.strip() for part in raw.split("^"))


def _normalize_date(value: Any, warnings: list[str]) -> str:
    raw = _clean(value)
    if not raw:
        return raw

    known_formats = ("%Y%m%d", "%Y-%m-%d", "%Y/%m/%d")
    for fmt in known_formats:
        try:
            return datetime.strptime(raw, fmt).strftime("%Y%m%d")
        except ValueError:
            continue

    warnings.append(f"study_date left unchanged due to unsupported format: '{raw}'")
    return raw


def _normalize_time(value: Any, warnings: list[str]) -> str:
    raw = _clean(value)
    if not raw:
        return raw

    compact = raw.replace(":", "")
    if "." in compact:
        hhmmss, fraction = compact.split(".", maxsplit=1)
        if hhmmss.isdigit() and fraction.isdigit():
            return f"{hhmmss[:6]}.{fraction[:6]}"
    if compact.isdigit():
        return compact[:6]

    warnings.append(f"study_time left unchanged due to unsupported format: '{raw}'")
    return raw


def _normalize_integer(value: Any, field: str, warnings: list[str]) -> str:
    raw = _clean(value)
    if not raw:
        return raw
    try:
        return str(int(raw))
    except ValueError:
        warnings.append(f"{field} left unchanged because it is not numeric: '{raw}'")
        return raw


def normalize_dataset(dataset: FileDataset) -> NormalizationResult:
    """Normalize common DICOM metadata fields for downstream consistency."""
    normalized = deepcopy(dataset)
    changes: list[NormalizationChange] = []
    warnings: list[str] = []

    for uid_field in ("StudyInstanceUID", "SeriesInstanceUID", "SOPInstanceUID", "SOPClassUID"):
        if hasattr(normalized, uid_field):
            _record_change(
                dataset=normalized,
                field=uid_field,
                current=getattr(normalized, uid_field),
                normalized=_clean(getattr(normalized, uid_field)),
                reason="trimmed whitespace",
                changes=changes,
            )

    if hasattr(normalized, "PatientID"):
        _record_change(
            dataset=normalized,
            field="PatientID",
            current=getattr(normalized, "PatientID"),
            normalized=_clean(getattr(normalized, "PatientID")),
            reason="trimmed whitespace",
            changes=changes,
        )

    if hasattr(normalized, "PatientName"):
        _record_change(
            dataset=normalized,
            field="PatientName",
            current=getattr(normalized, "PatientName"),
            normalized=_normalize_person_name(getattr(normalized, "PatientName")),
            reason="trimmed person-name components",
            changes=changes,
        )

    if hasattr(normalized, "AccessionNumber"):
        _record_change(
            dataset=normalized,
            field="AccessionNumber",
            current=getattr(normalized, "AccessionNumber"),
            normalized=_clean(getattr(normalized, "AccessionNumber")),
            reason="trimmed whitespace",
            changes=changes,
        )

    if hasattr(normalized, "Modality"):
        _record_change(
            dataset=normalized,
            field="Modality",
            current=getattr(normalized, "Modality"),
            normalized=_clean(getattr(normalized, "Modality")).upper(),
            reason="converted to uppercase and trimmed",
            changes=changes,
        )

    if hasattr(normalized, "StudyDate"):
        _record_change(
            dataset=normalized,
            field="StudyDate",
            current=getattr(normalized, "StudyDate"),
            normalized=_normalize_date(getattr(normalized, "StudyDate"), warnings),
            reason="normalized date to YYYYMMDD when parseable",
            changes=changes,
        )

    if hasattr(normalized, "StudyTime"):
        _record_change(
            dataset=normalized,
            field="StudyTime",
            current=getattr(normalized, "StudyTime"),
            normalized=_normalize_time(getattr(normalized, "StudyTime"), warnings),
            reason="normalized time to HHMMSS[.ffffff] when parseable",
            changes=changes,
        )

    if hasattr(normalized, "InstanceNumber"):
        _record_change(
            dataset=normalized,
            field="InstanceNumber",
            current=getattr(normalized, "InstanceNumber"),
            normalized=_normalize_integer(getattr(normalized, "InstanceNumber"), "instance_number", warnings),
            reason="normalized numeric representation",
            changes=changes,
        )

    return NormalizationResult(
        was_modified=len(changes) > 0,
        changes=changes,
        warnings=warnings,
        normalized_dataset=normalized,
    )


def normalize_file(
    file_path: str | Path,
    *,
    output_path: str | Path | None = None,
    overwrite: bool = False,
) -> NormalizationResult:
    """Normalize metadata from a DICOM file and optionally persist the result."""
    source = Path(file_path).expanduser().resolve()
    dataset = read_dicom_file(source, stop_before_pixels=False, force=False)
    result = normalize_dataset(dataset)

    if overwrite and output_path is not None:
        raise ValueError("overwrite and output_path are mutually exclusive")

    destination: Path | None = None
    if overwrite:
        destination = source
    elif output_path is not None:
        destination = Path(output_path).expanduser().resolve()

    if destination is not None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        result.normalized_dataset.save_as(str(destination))

    return result
