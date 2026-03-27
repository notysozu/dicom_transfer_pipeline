"""DICOM receiver AE and Storage SCP utilities (Steps 41-44)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from pydicom.dataset import Dataset
from pynetdicom import AE, AllStoragePresentationContexts, VerificationPresentationContexts
from pynetdicom.events import EVT_C_ECHO, EVT_C_STORE

from app.config import GuardianConfig, load_config
from app.security.tls import create_dicom_server_ssl_context


MAX_AE_TITLE_LENGTH = 16
DEFAULT_C_STORE_SUCCESS_STATUS = 0x0000
DEFAULT_C_STORE_FAILURE_STATUS = 0xC211
DEFAULT_INCOMING_STORAGE_ROOT = Path("data/incoming")


class ReceiverInitializationError(Exception):
    """Raised when the DICOM receiver AE cannot be initialized safely."""


@dataclass(frozen=True)
class ReceiverSettings:
    """Resolved receiver network settings for AE initialization."""

    ae_title: str
    host: str
    port: int
    max_associations: int
    acse_timeout: float
    dimse_timeout: float
    network_timeout: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReceiverInitializationResult:
    """Structured result returned after AE initialization."""

    ae: AE
    settings: ReceiverSettings
    supported_context_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "settings": self.settings.to_dict(),
            "supported_context_count": self.supported_context_count,
        }


@dataclass(frozen=True)
class StoredDatasetInfo:
    """Minimal metadata captured for an inbound C-STORE request."""

    sop_instance_uid: str
    study_instance_uid: str
    series_instance_uid: str
    sop_class_uid: str
    transfer_syntax_uid: str
    calling_ae_title: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class IncomingStorageResult:
    """Structured result for a dataset saved to incoming storage."""

    file_path: str
    file_name: str
    study_directory: str
    sop_instance_uid: str
    study_instance_uid: str
    file_size_bytes: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReceiverLogResult:
    """Structured result for an inbound dataset persisted and logged by the receiver."""

    transfer_uid: str
    incoming_storage: IncomingStorageResult
    transfer_record: dict[str, Any]
    study_metadata: dict[str, Any]
    instance_metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "transfer_uid": self.transfer_uid,
            "incoming_storage": self.incoming_storage.to_dict(),
            "transfer_record": dict(self.transfer_record),
            "study_metadata": dict(self.study_metadata),
            "instance_metadata": dict(self.instance_metadata),
        }


@dataclass(frozen=True)
class StorageScpResult:
    """Structured result for a started basic Storage SCP."""

    ae: AE
    settings: ReceiverSettings
    supported_context_count: int
    server: Any
    event_handlers: list[tuple[Any, Callable[..., Any]]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "settings": self.settings.to_dict(),
            "supported_context_count": self.supported_context_count,
            "event_handler_count": len(self.event_handlers),
        }


@dataclass(frozen=True)
class TlsStorageScpResult:
    """Structured result for a started TLS-enabled Storage SCP."""

    ae: AE
    settings: ReceiverSettings
    supported_context_count: int
    server: Any
    event_handlers: list[tuple[Any, Callable[..., Any]]]
    tls_client_cert_required: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "settings": self.settings.to_dict(),
            "supported_context_count": self.supported_context_count,
            "event_handler_count": len(self.event_handlers),
            "tls_client_cert_required": self.tls_client_cert_required,
        }


def _validate_ae_title(ae_title: str) -> str:
    normalized = str(ae_title).strip().upper()
    if not normalized:
        raise ReceiverInitializationError("dicom.ae_title cannot be empty")
    if len(normalized) > MAX_AE_TITLE_LENGTH:
        raise ReceiverInitializationError(
            f"dicom.ae_title must be {MAX_AE_TITLE_LENGTH} characters or fewer"
        )
    return normalized


def _validate_host(host: str) -> str:
    normalized = str(host).strip()
    if not normalized:
        raise ReceiverInitializationError("dicom.host cannot be empty")
    return normalized


def _validate_port(port: int) -> int:
    parsed = int(port)
    if not 1 <= parsed <= 65535:
        raise ReceiverInitializationError("dicom.port must be between 1 and 65535")
    return parsed


def _validate_positive_number(value: float, field_name: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise ReceiverInitializationError(f"{field_name} must be greater than 0")
    return parsed


def build_receiver_settings(
    config: GuardianConfig | None = None,
    *,
    max_associations: int = 10,
    acse_timeout: float = 30.0,
    dimse_timeout: float = 30.0,
    network_timeout: float = 30.0,
) -> ReceiverSettings:
    """Build validated receiver settings from guardian configuration."""
    active_config = config or load_config()
    return ReceiverSettings(
        ae_title=_validate_ae_title(active_config.dicom.ae_title),
        host=_validate_host(active_config.dicom.host),
        port=_validate_port(active_config.dicom.port),
        max_associations=int(_validate_positive_number(max_associations, "max_associations")),
        acse_timeout=_validate_positive_number(acse_timeout, "acse_timeout"),
        dimse_timeout=_validate_positive_number(dimse_timeout, "dimse_timeout"),
        network_timeout=_validate_positive_number(network_timeout, "network_timeout"),
    )


def initialize_receiver_ae(
    config: GuardianConfig | None = None,
    *,
    max_associations: int = 10,
    acse_timeout: float = 30.0,
    dimse_timeout: float = 30.0,
    network_timeout: float = 30.0,
) -> ReceiverInitializationResult:
    """Create and configure a pynetdicom AE for receiver-side SCP operation."""
    settings = build_receiver_settings(
        config,
        max_associations=max_associations,
        acse_timeout=acse_timeout,
        dimse_timeout=dimse_timeout,
        network_timeout=network_timeout,
    )

    ae = AE(ae_title=settings.ae_title)
    ae.maximum_associations = settings.max_associations
    ae.acse_timeout = settings.acse_timeout
    ae.dimse_timeout = settings.dimse_timeout
    ae.network_timeout = settings.network_timeout

    for context in VerificationPresentationContexts:
        ae.add_supported_context(context.abstract_syntax, context.transfer_syntax)
    for context in AllStoragePresentationContexts:
        ae.add_supported_context(context.abstract_syntax, context.transfer_syntax)

    return ReceiverInitializationResult(
        ae=ae,
        settings=settings,
        supported_context_count=len(ae.supported_contexts),
    )


def build_echo_handler() -> Callable[[Any], int]:
    """Build a basic C-ECHO handler that always acknowledges verification."""

    def handle_echo(event: Any) -> int:
        _ = event
        return 0x0000

    return handle_echo


def _dataset_to_info(event: Any) -> StoredDatasetInfo:
    dataset: Dataset = event.dataset
    dataset.file_meta = event.file_meta
    assoc = getattr(event, "assoc", None)
    requestor = getattr(assoc, "requestor", None)
    calling_ae_title = ""
    if requestor is not None and getattr(requestor, "ae_title", None):
        calling_ae_title = str(requestor.ae_title).strip()

    transfer_syntax_uid = ""
    if getattr(dataset, "file_meta", None) is not None:
        transfer_syntax_uid = str(getattr(dataset.file_meta, "TransferSyntaxUID", "")).strip()

    return StoredDatasetInfo(
        sop_instance_uid=str(getattr(dataset, "SOPInstanceUID", "")).strip(),
        study_instance_uid=str(getattr(dataset, "StudyInstanceUID", "")).strip(),
        series_instance_uid=str(getattr(dataset, "SeriesInstanceUID", "")).strip(),
        sop_class_uid=str(getattr(dataset, "SOPClassUID", "")).strip(),
        transfer_syntax_uid=transfer_syntax_uid,
        calling_ae_title=calling_ae_title,
    )


def _safe_path_component(value: str, *, fallback: str) -> str:
    cleaned = str(value).strip()
    if not cleaned:
        return fallback
    normalized = "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in cleaned)
    return normalized[:128] or fallback


def save_incoming_dataset(
    info: StoredDatasetInfo,
    dataset: Dataset,
    *,
    storage_root: str | Path = DEFAULT_INCOMING_STORAGE_ROOT,
) -> IncomingStorageResult:
    """Persist an inbound DICOM dataset into the incoming storage area."""
    root = Path(storage_root).expanduser().resolve()
    day_folder = datetime.utcnow().strftime("%Y%m%d")
    study_uid = _safe_path_component(info.study_instance_uid, fallback="unknown-study")
    sop_uid = _safe_path_component(info.sop_instance_uid, fallback=f"unknown-instance-{uuid4().hex}")

    study_directory = root / day_folder / study_uid
    study_directory.mkdir(parents=True, exist_ok=True)

    file_name = f"{sop_uid}.dcm"
    file_path = study_directory / file_name
    dataset.save_as(str(file_path), write_like_original=False)

    return IncomingStorageResult(
        file_path=str(file_path),
        file_name=file_name,
        study_directory=str(study_directory),
        sop_instance_uid=info.sop_instance_uid,
        study_instance_uid=info.study_instance_uid,
        file_size_bytes=file_path.stat().st_size,
    )


def build_incoming_storage_callback(
    *,
    storage_root: str | Path = DEFAULT_INCOMING_STORAGE_ROOT,
) -> Callable[[StoredDatasetInfo, Dataset], IncomingStorageResult]:
    """Build a callback that saves inbound DICOM datasets under data/incoming."""

    def store_incoming_dataset(info: StoredDatasetInfo, dataset: Dataset) -> IncomingStorageResult:
        return save_incoming_dataset(
            info,
            dataset,
            storage_root=storage_root,
        )

    return store_incoming_dataset


def log_received_dataset(
    info: StoredDatasetInfo,
    dataset: Dataset,
    *,
    storage_root: str | Path = DEFAULT_INCOMING_STORAGE_ROOT,
    db_path: str | Path | None = None,
    destination_ae_title: str | None = None,
) -> ReceiverLogResult:
    """Persist an inbound dataset and create transfer and metadata audit records."""
    from app.database.db import (
        create_transfer_record,
        initialize_database,
        upsert_instance_metadata,
        upsert_study_metadata,
    )

    incoming_storage = save_incoming_dataset(
        info,
        dataset,
        storage_root=storage_root,
    )
    initialize_database(db_path)

    transfer_uid = f"recv-{uuid4().hex}"
    receiver_ae_title = destination_ae_title or load_config().dicom.ae_title

    transfer_record = create_transfer_record(
        transfer_uid=transfer_uid,
        study_instance_uid=info.study_instance_uid or "UNAVAILABLE_STUDY_UID",
        sop_instance_uid=info.sop_instance_uid or None,
        source_ae_title=info.calling_ae_title or "UNKNOWN_MODALITY",
        destination_ae_title=str(receiver_ae_title).strip() or "DICOM_GUARDIAN",
        file_path=incoming_storage.file_path,
        file_size_bytes=incoming_storage.file_size_bytes,
        status="RECEIVED",
        db_path=db_path,
    )

    study_metadata = upsert_study_metadata(
        {
            "study_instance_uid": info.study_instance_uid,
            "patient_id": str(getattr(dataset, "PatientID", "")).strip(),
            "patient_name": str(getattr(dataset, "PatientName", "")).strip(),
            "accession_number": str(getattr(dataset, "AccessionNumber", "")).strip(),
            "study_date": str(getattr(dataset, "StudyDate", "")).strip(),
            "study_time": str(getattr(dataset, "StudyTime", "")).strip(),
            "modality": str(getattr(dataset, "Modality", "")).strip(),
            "study_description": str(getattr(dataset, "StudyDescription", "")).strip(),
            "referring_physician_name": str(getattr(dataset, "ReferringPhysicianName", "")).strip(),
            "institution_name": str(getattr(dataset, "InstitutionName", "")).strip(),
            "source_ae_title": info.calling_ae_title or "UNKNOWN_MODALITY",
            "total_instances": 1,
        },
        db_path=db_path,
    )

    instance_number = getattr(dataset, "InstanceNumber", None)
    try:
        normalized_instance_number = int(instance_number) if instance_number is not None else None
    except (TypeError, ValueError):
        normalized_instance_number = None

    instance_metadata = upsert_instance_metadata(
        {
            "study_instance_uid": info.study_instance_uid,
            "sop_instance_uid": info.sop_instance_uid,
            "series_instance_uid": info.series_instance_uid,
            "sop_class_uid": info.sop_class_uid,
            "instance_number": normalized_instance_number,
            "transfer_syntax_uid": info.transfer_syntax_uid,
            "file_path": incoming_storage.file_path,
            "checksum_sha256": None,
        },
        db_path=db_path,
    )

    return ReceiverLogResult(
        transfer_uid=transfer_uid,
        incoming_storage=incoming_storage,
        transfer_record=transfer_record,
        study_metadata=study_metadata,
        instance_metadata=instance_metadata,
    )


def build_incoming_storage_logging_callback(
    *,
    storage_root: str | Path = DEFAULT_INCOMING_STORAGE_ROOT,
    db_path: str | Path | None = None,
    destination_ae_title: str | None = None,
) -> Callable[[StoredDatasetInfo, Dataset], ReceiverLogResult]:
    """Build a callback that stores inbound datasets and logs receive records to SQLite."""

    def store_and_log_dataset(info: StoredDatasetInfo, dataset: Dataset) -> ReceiverLogResult:
        return log_received_dataset(
            info,
            dataset,
            storage_root=storage_root,
            db_path=db_path,
            destination_ae_title=destination_ae_title,
        )

    return store_and_log_dataset


def build_store_handler(
    *,
    on_dataset_received: Callable[[StoredDatasetInfo, Dataset], Any] | None = None,
) -> Callable[[Any], int]:
    """Build a basic C-STORE handler with an optional ingestion callback."""

    def handle_store(event: Any) -> int:
        dataset: Dataset = event.dataset
        dataset.file_meta = event.file_meta
        info = _dataset_to_info(event)

        if on_dataset_received is not None:
            try:
                on_dataset_received(info, dataset)
            except Exception:
                return DEFAULT_C_STORE_FAILURE_STATUS

        return DEFAULT_C_STORE_SUCCESS_STATUS

    return handle_store


def build_receiver_event_handlers(
    *,
    on_dataset_received: Callable[[StoredDatasetInfo, Dataset], Any] | None = None,
) -> list[tuple[Any, Callable[..., Any]]]:
    """Return the base event handlers for a non-TLS verification and storage SCP."""
    return [
        (EVT_C_ECHO, build_echo_handler()),
        (EVT_C_STORE, build_store_handler(on_dataset_received=on_dataset_received)),
    ]


def start_basic_storage_scp(
    config: GuardianConfig | None = None,
    *,
    max_associations: int = 10,
    acse_timeout: float = 30.0,
    dimse_timeout: float = 30.0,
    network_timeout: float = 30.0,
    block: bool = False,
    on_dataset_received: Callable[[StoredDatasetInfo, Dataset], Any] | None = None,
) -> StorageScpResult:
    """Start a basic non-TLS Storage SCP with C-ECHO and C-STORE support."""
    initialization = initialize_receiver_ae(
        config,
        max_associations=max_associations,
        acse_timeout=acse_timeout,
        dimse_timeout=dimse_timeout,
        network_timeout=network_timeout,
    )
    event_handlers = build_receiver_event_handlers(
        on_dataset_received=on_dataset_received,
    )
    server = initialization.ae.start_server(
        (initialization.settings.host, initialization.settings.port),
        block=block,
        evt_handlers=event_handlers,
    )
    return StorageScpResult(
        ae=initialization.ae,
        settings=initialization.settings,
        supported_context_count=initialization.supported_context_count,
        server=server,
        event_handlers=event_handlers,
    )


def start_tls_storage_scp(
    config: GuardianConfig | None = None,
    *,
    max_associations: int = 10,
    acse_timeout: float = 30.0,
    dimse_timeout: float = 30.0,
    network_timeout: float = 30.0,
    block: bool = False,
    require_client_cert: bool = True,
    on_dataset_received: Callable[[StoredDatasetInfo, Dataset], Any] | None = None,
) -> TlsStorageScpResult:
    """Start a TLS-enabled Storage SCP with C-ECHO and C-STORE support."""
    initialization = initialize_receiver_ae(
        config,
        max_associations=max_associations,
        acse_timeout=acse_timeout,
        dimse_timeout=dimse_timeout,
        network_timeout=network_timeout,
    )
    event_handlers = build_receiver_event_handlers(
        on_dataset_received=on_dataset_received,
    )
    ssl_context = create_dicom_server_ssl_context(
        None if config is None else config.tls,
        require_client_cert=require_client_cert,
    )
    server = initialization.ae.start_server(
        (initialization.settings.host, initialization.settings.port),
        block=block,
        evt_handlers=event_handlers,
        ssl_context=ssl_context,
    )
    return TlsStorageScpResult(
        ae=initialization.ae,
        settings=initialization.settings,
        supported_context_count=initialization.supported_context_count,
        server=server,
        event_handlers=event_handlers,
        tls_client_cert_required=require_client_cert,
    )
