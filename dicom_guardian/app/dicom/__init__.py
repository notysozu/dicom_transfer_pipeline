"""DICOM transport and processing components."""

from __future__ import annotations

from importlib import import_module
from typing import Any


_EXPORT_MAP = {
    "ChecksumError": ("app.dicom.checksum", "ChecksumError"),
    "ChecksumResult": ("app.dicom.checksum", "ChecksumResult"),
    "ChecksumVerificationResult": ("app.dicom.checksum", "ChecksumVerificationResult"),
    "CStoreSendResult": ("app.dicom.sender", "CStoreSendResult"),
    "CompressionError": ("app.dicom.compressor", "CompressionError"),
    "CompressionPolicy": ("app.dicom.compressor", "CompressionPolicy"),
    "CompressionResult": ("app.dicom.compressor", "CompressionResult"),
    "CorruptionDetectionResult": ("app.dicom.checksum", "CorruptionDetectionResult"),
    "build_compression_policy": ("app.dicom.compressor", "build_compression_policy"),
    "compress_dicom_file": ("app.dicom.compressor", "compress_dicom_file"),
    "detect_file_corruption": ("app.dicom.checksum", "detect_file_corruption"),
    "generate_file_checksum": ("app.dicom.checksum", "generate_file_checksum"),
    "generate_sha256": ("app.dicom.checksum", "generate_sha256"),
    "verify_file_checksum": ("app.dicom.checksum", "verify_file_checksum"),
    "NormalizationChange": ("app.dicom.normalizer", "NormalizationChange"),
    "NormalizationResult": ("app.dicom.normalizer", "NormalizationResult"),
    "normalize_dataset": ("app.dicom.normalizer", "normalize_dataset"),
    "normalize_file": ("app.dicom.normalizer", "normalize_file"),
    "IncomingStorageResult": ("app.dicom.receiver", "IncomingStorageResult"),
    "PacsAssociationNegotiationError": ("app.dicom.sender", "PacsAssociationNegotiationError"),
    "PacsAssociationNegotiationResult": ("app.dicom.sender", "PacsAssociationNegotiationResult"),
    "PacsClientInitializationError": ("app.dicom.sender", "PacsClientInitializationError"),
    "PacsClientInitializationResult": ("app.dicom.sender", "PacsClientInitializationResult"),
    "PacsClientSettings": ("app.dicom.sender", "PacsClientSettings"),
    "PacsSendError": ("app.dicom.sender", "PacsSendError"),
    "RequestedStorageContext": ("app.dicom.sender", "RequestedStorageContext"),
    "RetryAttemptResult": ("app.dicom.sender", "RetryAttemptResult"),
    "RetryPolicy": ("app.dicom.sender", "RetryPolicy"),
    "RetrySendResult": ("app.dicom.sender", "RetrySendResult"),
    "ReceiverInitializationError": ("app.dicom.receiver", "ReceiverInitializationError"),
    "ReceiverInitializationResult": ("app.dicom.receiver", "ReceiverInitializationResult"),
    "ReceiverLogResult": ("app.dicom.receiver", "ReceiverLogResult"),
    "ReceiverSettings": ("app.dicom.receiver", "ReceiverSettings"),
    "StorageScpResult": ("app.dicom.receiver", "StorageScpResult"),
    "StoredDatasetInfo": ("app.dicom.receiver", "StoredDatasetInfo"),
    "TlsStorageScpResult": ("app.dicom.receiver", "TlsStorageScpResult"),
    "build_incoming_storage_callback": ("app.dicom.receiver", "build_incoming_storage_callback"),
    "build_incoming_storage_logging_callback": ("app.dicom.receiver", "build_incoming_storage_logging_callback"),
    "build_pacs_client_settings": ("app.dicom.sender", "build_pacs_client_settings"),
    "build_requested_storage_contexts": ("app.dicom.sender", "build_requested_storage_contexts"),
    "build_retry_policy": ("app.dicom.sender", "build_retry_policy"),
    "build_echo_handler": ("app.dicom.receiver", "build_echo_handler"),
    "build_receiver_event_handlers": ("app.dicom.receiver", "build_receiver_event_handlers"),
    "build_receiver_settings": ("app.dicom.receiver", "build_receiver_settings"),
    "build_store_handler": ("app.dicom.receiver", "build_store_handler"),
    "initialize_receiver_ae": ("app.dicom.receiver", "initialize_receiver_ae"),
    "initialize_pacs_client_ae": ("app.dicom.sender", "initialize_pacs_client_ae"),
    "log_received_dataset": ("app.dicom.receiver", "log_received_dataset"),
    "negotiate_pacs_association": ("app.dicom.sender", "negotiate_pacs_association"),
    "TlsPacsAssociationNegotiationResult": ("app.dicom.sender", "TlsPacsAssociationNegotiationResult"),
    "negotiate_tls_pacs_association": ("app.dicom.sender", "negotiate_tls_pacs_association"),
    "send_c_store_to_pacs": ("app.dicom.sender", "send_c_store_to_pacs"),
    "send_c_store_to_pacs_with_retry": ("app.dicom.sender", "send_c_store_to_pacs_with_retry"),
    "send_c_store_to_tls_pacs": ("app.dicom.sender", "send_c_store_to_tls_pacs"),
    "send_c_store_to_tls_pacs_with_retry": ("app.dicom.sender", "send_c_store_to_tls_pacs_with_retry"),
    "send_c_store_via_association": ("app.dicom.sender", "send_c_store_via_association"),
    "send_c_store_with_retry": ("app.dicom.sender", "send_c_store_with_retry"),
    "save_incoming_dataset": ("app.dicom.receiver", "save_incoming_dataset"),
    "start_basic_storage_scp": ("app.dicom.receiver", "start_basic_storage_scp"),
    "start_tls_storage_scp": ("app.dicom.receiver", "start_tls_storage_scp"),
    "DicomReadError": ("app.dicom.reader", "DicomReadError"),
    "read_dicom_file": ("app.dicom.reader", "read_dicom_file"),
    "dataset_summary": ("app.dicom.reader", "dataset_summary"),
    "DicomMetadata": ("app.dicom.validator", "DicomMetadata"),
    "MetadataValidationResult": ("app.dicom.validator", "MetadataValidationResult"),
    "RejectionResult": ("app.dicom.validator", "RejectionResult"),
    "extract_metadata_from_dataset": ("app.dicom.validator", "extract_metadata_from_dataset"),
    "extract_metadata_from_file": ("app.dicom.validator", "extract_metadata_from_file"),
    "reject_invalid_study": ("app.dicom.validator", "reject_invalid_study"),
    "validate_metadata": ("app.dicom.validator", "validate_metadata"),
    "validate_metadata_from_file": ("app.dicom.validator", "validate_metadata_from_file"),
}

__all__ = list(_EXPORT_MAP)


def __getattr__(name: str) -> Any:
    """Lazy-load DICOM helpers so lightweight modules avoid heavy dependencies."""
    if name not in _EXPORT_MAP:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attribute_name = _EXPORT_MAP[name]
    module = import_module(module_name)
    value = getattr(module, attribute_name)
    globals()[name] = value
    return value
