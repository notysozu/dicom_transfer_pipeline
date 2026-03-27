"""DICOM PACS client initialization, negotiation, C-STORE sending, and retry utilities."""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from ssl import SSLContext
from typing import Any, Callable, Iterable

from pydicom.uid import ImplicitVRLittleEndian, UID
from pynetdicom import AE, VerificationPresentationContexts

from app.config import GuardianConfig, load_config
from app.dicom.reader import read_dicom_file
from app.security.tls import create_outbound_client_ssl_context


MAX_AE_TITLE_LENGTH = 16
MAX_REQUESTED_PRESENTATION_CONTEXTS = 128
DEFAULT_C_STORE_SUCCESS_STATUS = 0x0000


class PacsClientInitializationError(Exception):
    """Raised when the outbound PACS client cannot be initialized safely."""


class PacsAssociationNegotiationError(Exception):
    """Raised when PACS association negotiation cannot be completed safely."""


class PacsSendError(Exception):
    """Raised when a DICOM object cannot be sent to PACS safely."""


@dataclass(frozen=True)
class PacsClientSettings:
    """Resolved outbound PACS client settings for SCU initialization."""

    calling_ae_title: str
    pacs_ae_title: str
    pacs_host: str
    pacs_port: int
    acse_timeout: float
    dimse_timeout: float
    network_timeout: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RequestedStorageContext:
    """Single storage presentation context request for PACS negotiation."""

    abstract_syntax_uid: str
    transfer_syntax_uids: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PacsClientInitializationResult:
    """Structured result returned after PACS client AE initialization."""

    ae: AE
    settings: PacsClientSettings
    requested_context_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "settings": self.settings.to_dict(),
            "requested_context_count": self.requested_context_count,
        }


@dataclass(frozen=True)
class PacsAssociationNegotiationResult:
    """Structured result returned after PACS association negotiation."""

    ae: AE
    association: Any
    settings: PacsClientSettings
    requested_contexts: list[RequestedStorageContext]
    requested_context_count: int
    is_established: bool
    tls_enabled: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "settings": self.settings.to_dict(),
            "requested_contexts": [item.to_dict() for item in self.requested_contexts],
            "requested_context_count": self.requested_context_count,
            "is_established": self.is_established,
            "tls_enabled": self.tls_enabled,
        }


@dataclass(frozen=True)
class TlsPacsAssociationNegotiationResult:
    """Structured result returned after TLS PACS association negotiation."""

    ae: AE
    association: Any
    settings: PacsClientSettings
    requested_contexts: list[RequestedStorageContext]
    requested_context_count: int
    is_established: bool
    tls_enabled: bool
    tls_check_hostname: bool
    tls_present_client_certificate: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "settings": self.settings.to_dict(),
            "requested_contexts": [item.to_dict() for item in self.requested_contexts],
            "requested_context_count": self.requested_context_count,
            "is_established": self.is_established,
            "tls_enabled": self.tls_enabled,
            "tls_check_hostname": self.tls_check_hostname,
            "tls_present_client_certificate": self.tls_present_client_certificate,
        }


@dataclass(frozen=True)
class CStoreSendResult:
    """Structured result returned after a single C-STORE transmission."""

    file_path: str
    sop_instance_uid: str
    study_instance_uid: str
    sop_class_uid: str
    transfer_syntax_uid: str
    requested_context_count: int
    is_established: bool
    tls_enabled: bool
    status: int | None
    success: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RetryPolicy:
    """Retry policy for PACS send attempts."""

    max_attempts: int = 3
    backoff_seconds: float = 1.0
    backoff_multiplier: float = 2.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RetryAttemptResult:
    """Outcome of a single PACS retry attempt."""

    attempt_number: int
    success: bool
    error_message: str | None = None
    send_result: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RetrySendResult:
    """Aggregated outcome of a retry-enabled PACS send."""

    file_path: str
    success: bool
    total_attempts: int
    final_result: dict[str, Any] | None
    attempts: list[RetryAttemptResult]

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path": self.file_path,
            "success": self.success,
            "total_attempts": self.total_attempts,
            "final_result": self.final_result,
            "attempts": [item.to_dict() for item in self.attempts],
        }


def _validate_ae_title(ae_title: str, field_name: str) -> str:
    normalized = str(ae_title).strip().upper()
    if not normalized:
        raise PacsClientInitializationError(f"{field_name} cannot be empty")
    if len(normalized) > MAX_AE_TITLE_LENGTH:
        raise PacsClientInitializationError(
            f"{field_name} must be {MAX_AE_TITLE_LENGTH} characters or fewer"
        )
    return normalized


def _validate_host(host: str, field_name: str) -> str:
    normalized = str(host).strip()
    if not normalized:
        raise PacsClientInitializationError(f"{field_name} cannot be empty")
    return normalized


def _validate_port(port: int, field_name: str) -> int:
    parsed = int(port)
    if not 1 <= parsed <= 65535:
        raise PacsClientInitializationError(f"{field_name} must be between 1 and 65535")
    return parsed


def _validate_positive_number(value: float, field_name: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise PacsClientInitializationError(f"{field_name} must be greater than 0")
    return parsed


def _normalize_uid(uid: str, field_name: str) -> str:
    normalized = str(uid).strip()
    if not normalized:
        raise PacsAssociationNegotiationError(f"{field_name} cannot be empty")
    try:
        parsed = UID(normalized)
    except Exception as exc:  # pragma: no cover
        raise PacsAssociationNegotiationError(f"{field_name} is not a valid UID: {normalized}") from exc
    if not parsed:
        raise PacsAssociationNegotiationError(f"{field_name} is not a valid UID: {normalized}")
    return str(parsed)


def _validate_requested_context_limit(context_count: int) -> None:
    if context_count > MAX_REQUESTED_PRESENTATION_CONTEXTS:
        raise PacsAssociationNegotiationError(
            "requested presentation contexts exceed the DICOM limit of "
            f"{MAX_REQUESTED_PRESENTATION_CONTEXTS}"
        )


def _normalize_status_code(status: Any) -> int | None:
    if status is None:
        return None
    if isinstance(status, int):
        return status
    if hasattr(status, "Status"):
        try:
            return int(status.Status)
        except (TypeError, ValueError):
            return None
    return None


def build_retry_policy(
    *,
    max_attempts: int = 3,
    backoff_seconds: float = 1.0,
    backoff_multiplier: float = 2.0,
) -> RetryPolicy:
    """Build and validate a retry policy for PACS send attempts."""
    normalized_attempts = int(max_attempts)
    normalized_backoff_seconds = float(backoff_seconds)
    normalized_multiplier = float(backoff_multiplier)

    if normalized_attempts < 1:
        raise ValueError("max_attempts must be >= 1")
    if normalized_backoff_seconds < 0:
        raise ValueError("backoff_seconds must be >= 0")
    if normalized_multiplier < 1:
        raise ValueError("backoff_multiplier must be >= 1")

    return RetryPolicy(
        max_attempts=normalized_attempts,
        backoff_seconds=normalized_backoff_seconds,
        backoff_multiplier=normalized_multiplier,
    )


def _build_association_ae(
    *,
    requested_contexts: list[RequestedStorageContext] | None,
    config: GuardianConfig | None,
    request_verification: bool,
    acse_timeout: float,
    dimse_timeout: float,
    network_timeout: float,
) -> tuple[AE, PacsClientSettings, list[RequestedStorageContext]]:
    initialization = initialize_pacs_client_ae(
        config,
        request_verification=request_verification,
        acse_timeout=acse_timeout,
        dimse_timeout=dimse_timeout,
        network_timeout=network_timeout,
    )
    ae = initialization.ae
    normalized_requested_contexts = list(requested_contexts or [])
    total_requested_context_count = len(ae.requested_contexts) + len(normalized_requested_contexts)
    _validate_requested_context_limit(total_requested_context_count)

    for requested_context in normalized_requested_contexts:
        ae.add_requested_context(
            UID(requested_context.abstract_syntax_uid),
            [UID(item) for item in requested_context.transfer_syntax_uids],
        )

    return ae, initialization.settings, normalized_requested_contexts


def build_pacs_client_settings(
    config: GuardianConfig | None = None,
    *,
    acse_timeout: float = 30.0,
    dimse_timeout: float = 30.0,
    network_timeout: float = 30.0,
) -> PacsClientSettings:
    """Build validated PACS client settings from guardian configuration."""
    active_config = config or load_config()
    return PacsClientSettings(
        calling_ae_title=_validate_ae_title(active_config.dicom.ae_title, "dicom.ae_title"),
        pacs_ae_title=_validate_ae_title(active_config.pacs.ae_title, "pacs.ae_title"),
        pacs_host=_validate_host(active_config.pacs.host, "pacs.host"),
        pacs_port=_validate_port(active_config.pacs.port, "pacs.port"),
        acse_timeout=_validate_positive_number(acse_timeout, "acse_timeout"),
        dimse_timeout=_validate_positive_number(dimse_timeout, "dimse_timeout"),
        network_timeout=_validate_positive_number(network_timeout, "network_timeout"),
    )


def build_requested_storage_contexts(
    *,
    sop_class_uid: str,
    transfer_syntax_uids: Iterable[str] | None = None,
) -> list[RequestedStorageContext]:
    """Build requested storage presentation contexts for specific SOP classes."""
    normalized_sop_class_uid = _normalize_uid(sop_class_uid, "sop_class_uid")
    normalized_transfer_syntax_uids: list[str] = []

    for transfer_syntax_uid in transfer_syntax_uids or [str(ImplicitVRLittleEndian)]:
        normalized_transfer_syntax_uids.append(
            _normalize_uid(transfer_syntax_uid, "transfer_syntax_uid")
        )

    unique_transfer_syntax_uids = list(dict.fromkeys(normalized_transfer_syntax_uids))
    return [
        RequestedStorageContext(
            abstract_syntax_uid=normalized_sop_class_uid,
            transfer_syntax_uids=unique_transfer_syntax_uids,
        )
    ]


def initialize_pacs_client_ae(
    config: GuardianConfig | None = None,
    *,
    request_verification: bool = True,
    acse_timeout: float = 30.0,
    dimse_timeout: float = 30.0,
    network_timeout: float = 30.0,
) -> PacsClientInitializationResult:
    """Create and configure a base pynetdicom AE for outbound PACS SCU operations."""
    settings = build_pacs_client_settings(
        config,
        acse_timeout=acse_timeout,
        dimse_timeout=dimse_timeout,
        network_timeout=network_timeout,
    )

    ae = AE(ae_title=settings.calling_ae_title)
    ae.acse_timeout = settings.acse_timeout
    ae.dimse_timeout = settings.dimse_timeout
    ae.network_timeout = settings.network_timeout

    if request_verification:
        for context in VerificationPresentationContexts:
            ae.add_requested_context(context.abstract_syntax, context.transfer_syntax)

    return PacsClientInitializationResult(
        ae=ae,
        settings=settings,
        requested_context_count=len(ae.requested_contexts),
    )


def negotiate_pacs_association(
    *,
    requested_contexts: list[RequestedStorageContext] | None = None,
    config: GuardianConfig | None = None,
    request_verification: bool = True,
    acse_timeout: float = 30.0,
    dimse_timeout: float = 30.0,
    network_timeout: float = 30.0,
) -> PacsAssociationNegotiationResult:
    """Negotiate a non-TLS association to the configured PACS target."""
    ae, settings, normalized_requested_contexts = _build_association_ae(
        requested_contexts=requested_contexts,
        config=config,
        request_verification=request_verification,
        acse_timeout=acse_timeout,
        dimse_timeout=dimse_timeout,
        network_timeout=network_timeout,
    )

    association = ae.associate(
        settings.pacs_host,
        settings.pacs_port,
        ae_title=settings.pacs_ae_title,
    )
    return PacsAssociationNegotiationResult(
        ae=ae,
        association=association,
        settings=settings,
        requested_contexts=normalized_requested_contexts,
        requested_context_count=len(ae.requested_contexts),
        is_established=bool(getattr(association, "is_established", False)),
        tls_enabled=False,
    )


def negotiate_tls_pacs_association(
    *,
    requested_contexts: list[RequestedStorageContext] | None = None,
    config: GuardianConfig | None = None,
    request_verification: bool = True,
    acse_timeout: float = 30.0,
    dimse_timeout: float = 30.0,
    network_timeout: float = 30.0,
    check_hostname: bool = True,
    present_client_certificate: bool = True,
    ssl_context: SSLContext | None = None,
) -> TlsPacsAssociationNegotiationResult:
    """Negotiate a TLS-protected association to the configured PACS target."""
    ae, settings, normalized_requested_contexts = _build_association_ae(
        requested_contexts=requested_contexts,
        config=config,
        request_verification=request_verification,
        acse_timeout=acse_timeout,
        dimse_timeout=dimse_timeout,
        network_timeout=network_timeout,
    )

    outbound_ssl_context = ssl_context or create_outbound_client_ssl_context(
        None if config is None else config.tls,
        check_hostname=check_hostname,
        present_client_certificate=present_client_certificate,
    )

    association = ae.associate(
        settings.pacs_host,
        settings.pacs_port,
        ae_title=settings.pacs_ae_title,
        tls_args=(outbound_ssl_context, settings.pacs_host),
    )
    return TlsPacsAssociationNegotiationResult(
        ae=ae,
        association=association,
        settings=settings,
        requested_contexts=normalized_requested_contexts,
        requested_context_count=len(ae.requested_contexts),
        is_established=bool(getattr(association, "is_established", False)),
        tls_enabled=True,
        tls_check_hostname=check_hostname,
        tls_present_client_certificate=present_client_certificate,
    )


def send_c_store_via_association(
    *,
    association: Any,
    file_path: str,
    requested_context_count: int,
    tls_enabled: bool,
) -> CStoreSendResult:
    """Send a DICOM file over an already established association."""
    dataset = read_dicom_file(file_path, stop_before_pixels=False, force=False)
    if not getattr(association, "is_established", False):
        raise PacsSendError("PACS association is not established")

    status = association.send_c_store(dataset)
    normalized_status = _normalize_status_code(status)

    return CStoreSendResult(
        file_path=str(file_path),
        sop_instance_uid=str(getattr(dataset, "SOPInstanceUID", "")).strip(),
        study_instance_uid=str(getattr(dataset, "StudyInstanceUID", "")).strip(),
        sop_class_uid=str(getattr(dataset, "SOPClassUID", "")).strip(),
        transfer_syntax_uid=str(getattr(getattr(dataset, "file_meta", None), "TransferSyntaxUID", "")).strip(),
        requested_context_count=int(requested_context_count),
        is_established=bool(getattr(association, "is_established", False)),
        tls_enabled=bool(tls_enabled),
        status=normalized_status,
        success=normalized_status == DEFAULT_C_STORE_SUCCESS_STATUS,
    )


def send_c_store_to_pacs(
    file_path: str,
    *,
    config: GuardianConfig | None = None,
    request_verification: bool = True,
    acse_timeout: float = 30.0,
    dimse_timeout: float = 30.0,
    network_timeout: float = 30.0,
    release_association: bool = True,
) -> CStoreSendResult:
    """Negotiate a non-TLS PACS association and send one DICOM object via C-STORE."""
    dataset = read_dicom_file(file_path, stop_before_pixels=False, force=False)
    requested_contexts = build_requested_storage_contexts(
        sop_class_uid=str(getattr(dataset, "SOPClassUID", "")).strip(),
        transfer_syntax_uids=[
            str(getattr(getattr(dataset, "file_meta", None), "TransferSyntaxUID", "")).strip()
            or str(ImplicitVRLittleEndian)
        ],
    )
    negotiation = negotiate_pacs_association(
        requested_contexts=requested_contexts,
        config=config,
        request_verification=request_verification,
        acse_timeout=acse_timeout,
        dimse_timeout=dimse_timeout,
        network_timeout=network_timeout,
    )
    if not negotiation.is_established:
        raise PacsSendError("Failed to establish PACS association for C-STORE")

    try:
        return send_c_store_via_association(
            association=negotiation.association,
            file_path=file_path,
            requested_context_count=negotiation.requested_context_count,
            tls_enabled=False,
        )
    finally:
        if release_association and getattr(negotiation.association, "is_established", False):
            negotiation.association.release()


def send_c_store_to_tls_pacs(
    file_path: str,
    *,
    config: GuardianConfig | None = None,
    request_verification: bool = True,
    acse_timeout: float = 30.0,
    dimse_timeout: float = 30.0,
    network_timeout: float = 30.0,
    check_hostname: bool = True,
    present_client_certificate: bool = True,
    ssl_context: SSLContext | None = None,
    release_association: bool = True,
) -> CStoreSendResult:
    """Negotiate a TLS PACS association and send one DICOM object via C-STORE."""
    dataset = read_dicom_file(file_path, stop_before_pixels=False, force=False)
    requested_contexts = build_requested_storage_contexts(
        sop_class_uid=str(getattr(dataset, "SOPClassUID", "")).strip(),
        transfer_syntax_uids=[
            str(getattr(getattr(dataset, "file_meta", None), "TransferSyntaxUID", "")).strip()
            or str(ImplicitVRLittleEndian)
        ],
    )
    negotiation = negotiate_tls_pacs_association(
        requested_contexts=requested_contexts,
        config=config,
        request_verification=request_verification,
        acse_timeout=acse_timeout,
        dimse_timeout=dimse_timeout,
        network_timeout=network_timeout,
        check_hostname=check_hostname,
        present_client_certificate=present_client_certificate,
        ssl_context=ssl_context,
    )
    if not negotiation.is_established:
        raise PacsSendError("Failed to establish TLS PACS association for C-STORE")

    try:
        return send_c_store_via_association(
            association=negotiation.association,
            file_path=file_path,
            requested_context_count=negotiation.requested_context_count,
            tls_enabled=True,
        )
    finally:
        if release_association and getattr(negotiation.association, "is_established", False):
            negotiation.association.release()


def send_c_store_with_retry(
    file_path: str,
    *,
    retry_policy: RetryPolicy | None = None,
    send_callable: Callable[..., CStoreSendResult] = send_c_store_to_pacs,
    **send_kwargs: Any,
) -> RetrySendResult:
    """Send a DICOM file with retries using the provided send callable."""
    policy = retry_policy or build_retry_policy()
    attempts: list[RetryAttemptResult] = []
    final_result: dict[str, Any] | None = None
    delay_seconds = policy.backoff_seconds

    for attempt_number in range(1, policy.max_attempts + 1):
        try:
            send_result = send_callable(file_path, **send_kwargs)
            final_result = send_result.to_dict()
            attempt_record = RetryAttemptResult(
                attempt_number=attempt_number,
                success=send_result.success,
                error_message=None if send_result.success else "C-STORE returned non-success status",
                send_result=final_result,
            )
            attempts.append(attempt_record)
            if send_result.success:
                return RetrySendResult(
                    file_path=str(file_path),
                    success=True,
                    total_attempts=attempt_number,
                    final_result=final_result,
                    attempts=attempts,
                )
        except Exception as exc:
            attempts.append(
                RetryAttemptResult(
                    attempt_number=attempt_number,
                    success=False,
                    error_message=str(exc),
                    send_result=None,
                )
            )

        if attempt_number < policy.max_attempts and delay_seconds > 0:
            time.sleep(delay_seconds)
            delay_seconds *= policy.backoff_multiplier

    return RetrySendResult(
        file_path=str(file_path),
        success=False,
        total_attempts=policy.max_attempts,
        final_result=final_result,
        attempts=attempts,
    )


def send_c_store_to_pacs_with_retry(
    file_path: str,
    *,
    retry_policy: RetryPolicy | None = None,
    **send_kwargs: Any,
) -> RetrySendResult:
    """Retry-enabled wrapper for non-TLS PACS sends."""
    return send_c_store_with_retry(
        file_path,
        retry_policy=retry_policy,
        send_callable=send_c_store_to_pacs,
        **send_kwargs,
    )


def send_c_store_to_tls_pacs_with_retry(
    file_path: str,
    *,
    retry_policy: RetryPolicy | None = None,
    **send_kwargs: Any,
) -> RetrySendResult:
    """Retry-enabled wrapper for TLS PACS sends."""
    return send_c_store_with_retry(
        file_path,
        retry_policy=retry_policy,
        send_callable=send_c_store_to_tls_pacs,
        **send_kwargs,
    )
