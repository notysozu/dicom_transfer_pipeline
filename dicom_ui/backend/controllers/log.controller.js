'use strict';

const { DicomGuardianServiceError, getGuardianLogs } = require('../services/dicomGuardian.service');

function normalizeOptionalString(value) {
  if (typeof value !== 'string') {
    return undefined;
  }

  const trimmed = value.trim();
  return trimmed ? trimmed : undefined;
}

function normalizeLimit(value, fallback = 100) {
  if (value === undefined || value === null || value === '') {
    return fallback;
  }

  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed < 1 || parsed > 1000) {
    throw new Error('limit must be an integer between 1 and 1000');
  }

  return parsed;
}

function buildLogSearchQuery(req) {
  return {
    sop_instance_uid: normalizeOptionalString(req.query?.sop_instance_uid),
    study_instance_uid: normalizeOptionalString(req.query?.study_instance_uid),
    status: normalizeOptionalString(req.query?.status),
    limit: normalizeLimit(req.query?.limit),
  };
}

async function listLogs(req, res) {
  let query;

  try {
    query = buildLogSearchQuery(req);
  } catch (error) {
    return res.status(400).json({
      error: 'validation_error',
      message: error.message,
    });
  }

  try {
    const guardianResponse = await getGuardianLogs(query);
    const payload = guardianResponse.body && typeof guardianResponse.body === 'object'
      ? guardianResponse.body
      : {};

    return res.status(200).json({
      source: 'dicom_guardian',
      count: typeof payload.count === 'number' ? payload.count : 0,
      filters: payload.filters || query,
      logs: Array.isArray(payload.logs) ? payload.logs : [],
    });
  } catch (error) {
    if (error instanceof DicomGuardianServiceError) {
      const upstreamStatus = error.details?.statusCode || 502;
      const responseStatus = upstreamStatus >= 500 ? 502 : upstreamStatus;

      return res.status(responseStatus).json({
        error: 'guardian_request_failed',
        message: error.message,
        details: error.details,
      });
    }

    return res.status(500).json({
      error: 'log_retrieval_failed',
      message: error.message,
    });
  }
}

module.exports = {
  buildLogSearchQuery,
  listLogs,
};
