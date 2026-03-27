'use strict';

const fs = require('node:fs');
const https = require('node:https');
const path = require('node:path');

const { buildConfigFromEnv } = require('../config');

const PROJECT_ROOT = path.resolve(__dirname, '../..');

class DicomGuardianServiceError extends Error {
  constructor(message, details = {}) {
    super(message);
    this.name = 'DicomGuardianServiceError';
    this.details = details;
  }
}

function resolveGuardianCaPath(caPath, cwd = process.cwd()) {
  const resolvedPath = path.isAbsolute(caPath)
    ? caPath
    : path.resolve(PROJECT_ROOT, caPath);

  if (!fs.existsSync(resolvedPath)) {
    throw new DicomGuardianServiceError('Guardian CA file does not exist', {
      caPath: resolvedPath,
    });
  }

  const stat = fs.statSync(resolvedPath);
  if (!stat.isFile() || stat.size <= 0) {
    throw new DicomGuardianServiceError('Guardian CA file is invalid', {
      caPath: resolvedPath,
    });
  }

  return resolvedPath;
}

function buildGuardianServiceConfig(config = buildConfigFromEnv(), cwd = process.cwd()) {
  const baseUrl = new URL(config.app.guardian.baseUrl);
  const timeoutMs = config.app.guardian.timeoutMs;
  const caPath = resolveGuardianCaPath(config.app.guardian.caPath, cwd);

  return Object.freeze({
    baseUrl: baseUrl.toString(),
    origin: baseUrl.origin,
    protocol: baseUrl.protocol,
    hostname: baseUrl.hostname,
    port: baseUrl.port ? Number(baseUrl.port) : 443,
    timeoutMs,
    caPath,
    rejectUnauthorized: config.tls.rejectUnauthorized,
  });
}

function buildGuardianUrl(pathname, query = {}, serviceConfig = buildGuardianServiceConfig()) {
  const url = new URL(pathname, serviceConfig.baseUrl);

  Object.entries(query || {}).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') {
      return;
    }
    url.searchParams.set(key, String(value));
  });

  return url;
}

function normalizeGuardianResponseBody(rawBody) {
  if (!rawBody) {
    return null;
  }

  try {
    return JSON.parse(rawBody);
  } catch (_error) {
    return rawBody;
  }
}

function requestGuardian(
  pathname,
  {
    method = 'GET',
    query = {},
    body = null,
    headers = {},
    config,
  } = {}
) {
  const serviceConfig = buildGuardianServiceConfig(config);
  const url = buildGuardianUrl(pathname, query, serviceConfig);
  const payload = body ? JSON.stringify(body) : null;
  const ca = fs.readFileSync(serviceConfig.caPath);

  return new Promise((resolve, reject) => {
    const request = https.request(
      url,
      {
        method,
        ca,
        rejectUnauthorized: serviceConfig.rejectUnauthorized,
        minVersion: 'TLSv1.2',
        headers: {
          Accept: 'application/json',
          ...(payload
            ? {
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(payload),
              }
            : {}),
          ...headers,
        },
      },
      (response) => {
        let rawBody = '';

        response.setEncoding('utf8');
        response.on('data', (chunk) => {
          rawBody += chunk;
        });

        response.on('end', () => {
          const normalizedBody = normalizeGuardianResponseBody(rawBody);
          const result = {
            statusCode: response.statusCode || 0,
            headers: response.headers,
            body: normalizedBody,
          };

          if ((response.statusCode || 500) >= 400) {
            return reject(
              new DicomGuardianServiceError('Guardian API request failed', {
                ...result,
                url: url.toString(),
                method,
              })
            );
          }

          return resolve(result);
        });
      }
    );

    request.setTimeout(serviceConfig.timeoutMs, () => {
      request.destroy(
        new DicomGuardianServiceError('Guardian API request timed out', {
          url: url.toString(),
          method,
          timeoutMs: serviceConfig.timeoutMs,
        })
      );
    });

    request.on('error', (error) => {
      reject(
        error instanceof DicomGuardianServiceError
          ? error
          : new DicomGuardianServiceError(error.message, {
              url: url.toString(),
              method,
            })
      );
    });

    if (payload) {
      request.write(payload);
    }

    request.end();
  });
}

async function getGuardianStudies(query = {}, config) {
  return requestGuardian('/api/studies', { method: 'GET', query, config });
}

async function getGuardianTransfers(query = {}, config) {
  return requestGuardian('/api/transfers', { method: 'GET', query, config });
}

async function getGuardianLogs(query = {}, config) {
  return requestGuardian('/api/logs', { method: 'GET', query, config });
}

async function getGuardianMetrics(config) {
  return requestGuardian('/api/metrics', { method: 'GET', config });
}

async function retrieveGuardianStudy(body = {}, config) {
  return requestGuardian('/api/retrieve-study', {
    method: 'POST',
    body,
    config,
  });
}

module.exports = {
  DicomGuardianServiceError,
  buildGuardianServiceConfig,
  buildGuardianUrl,
  requestGuardian,
  getGuardianStudies,
  getGuardianTransfers,
  getGuardianLogs,
  getGuardianMetrics,
  retrieveGuardianStudy,
};
