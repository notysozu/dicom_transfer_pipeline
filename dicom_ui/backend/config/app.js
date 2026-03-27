'use strict';

/**
 * Central configuration management for dicom_ui backend.
 *
 * Step 9 introduces configuration shape and validation.
 * Environment variable binding is added in Step 10.
 */

const DEFAULT_CONFIG = Object.freeze({
  environment: 'development',
  server: {
    host: '0.0.0.0',
    port: 9443,
  },
  jwt: {
    secret: 'replace-with-secure-random-secret',
    expiresIn: '1h',
    issuer: 'dicom_ui_backend',
    audience: 'dicom_ui_clients',
  },
  guardian: {
    baseUrl: 'https://127.0.0.1:8443',
    timeoutMs: 10000,
    caPath: './backend/certificates/guardian-ca.pem',
  },
  logging: {
    level: 'info',
  },
});

function isPlainObject(value) {
  return value && typeof value === 'object' && !Array.isArray(value);
}

function deepMerge(base, override) {
  const merged = { ...base };

  for (const [key, value] of Object.entries(override || {})) {
    if (isPlainObject(value) && isPlainObject(base[key])) {
      merged[key] = deepMerge(base[key], value);
      continue;
    }

    merged[key] = value;
  }

  return merged;
}

function requireNonEmpty(value, fieldName) {
  if (typeof value !== 'string' || value.trim().length === 0) {
    throw new Error(`${fieldName} must be a non-empty string`);
  }

  return value.trim();
}

function requirePort(value, fieldName) {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed < 1 || parsed > 65535) {
    throw new Error(`${fieldName} must be an integer between 1 and 65535`);
  }

  return parsed;
}

function requirePositiveInt(value, fieldName) {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed < 1) {
    throw new Error(`${fieldName} must be a positive integer`);
  }

  return parsed;
}

function buildAppConfig(overrides = {}) {
  const raw = deepMerge(DEFAULT_CONFIG, overrides);

  return Object.freeze({
    environment: requireNonEmpty(raw.environment, 'environment'),
    server: Object.freeze({
      host: requireNonEmpty(raw.server.host, 'server.host'),
      port: requirePort(raw.server.port, 'server.port'),
    }),
    jwt: Object.freeze({
      secret: requireNonEmpty(raw.jwt.secret, 'jwt.secret'),
      expiresIn: requireNonEmpty(raw.jwt.expiresIn, 'jwt.expiresIn'),
      issuer: requireNonEmpty(raw.jwt.issuer, 'jwt.issuer'),
      audience: requireNonEmpty(raw.jwt.audience, 'jwt.audience'),
    }),
    guardian: Object.freeze({
      baseUrl: requireNonEmpty(raw.guardian.baseUrl, 'guardian.baseUrl'),
      timeoutMs: requirePositiveInt(raw.guardian.timeoutMs, 'guardian.timeoutMs'),
      caPath: requireNonEmpty(raw.guardian.caPath, 'guardian.caPath'),
    }),
    logging: Object.freeze({
      level: requireNonEmpty(raw.logging.level, 'logging.level'),
    }),
  });
}

module.exports = {
  DEFAULT_CONFIG,
  buildAppConfig,
};
