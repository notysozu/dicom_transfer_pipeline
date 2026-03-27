'use strict';

const fs = require('node:fs');
const path = require('node:path');
const dotenv = require('dotenv');

function loadEnvFile() {
  const explicitPath = process.env.DICOM_UI_ENV_FILE;
  if (explicitPath) {
    dotenv.config({ path: explicitPath });
    return explicitPath;
  }

  const projectEnvPath = path.resolve(__dirname, '../../.env');
  if (fs.existsSync(projectEnvPath)) {
    dotenv.config({ path: projectEnvPath });
    return projectEnvPath;
  }

  dotenv.config();
  return null;
}

function parseOptionalInt(value, fieldName) {
  if (value === undefined || value === null || value === '') {
    return undefined;
  }

  const parsed = Number(value);
  if (!Number.isInteger(parsed)) {
    throw new Error(`${fieldName} must be an integer`);
  }

  return parsed;
}

function parseOptionalBoolean(value, fieldName) {
  if (value === undefined || value === null || value === '') {
    return undefined;
  }

  const normalized = String(value).trim().toLowerCase();
  if (normalized === 'true') {
    return true;
  }
  if (normalized === 'false') {
    return false;
  }

  throw new Error(`${fieldName} must be true or false`);
}

function buildOverridesFromEnv(env = process.env) {
  const appOverrides = {};
  const dbOverrides = {};
  const tlsOverrides = {};

  if (env.NODE_ENV) {
    appOverrides.environment = env.NODE_ENV;
  }
  if (env.UI_BACKEND_HOST || env.UI_BACKEND_PORT) {
    appOverrides.server = {};
    if (env.UI_BACKEND_HOST) {
      appOverrides.server.host = env.UI_BACKEND_HOST;
    }
    if (env.UI_BACKEND_PORT) {
      appOverrides.server.port = parseOptionalInt(env.UI_BACKEND_PORT, 'UI_BACKEND_PORT');
    }
  }
  if (env.JWT_EXPIRES_IN) {
    appOverrides.jwt = appOverrides.jwt || {};
    appOverrides.jwt.expiresIn = env.JWT_EXPIRES_IN;
  }
  if (env.JWT_SECRET) {
    appOverrides.jwt = appOverrides.jwt || {};
    appOverrides.jwt.secret = env.JWT_SECRET;
  }
  if (env.JWT_ISSUER) {
    appOverrides.jwt = appOverrides.jwt || {};
    appOverrides.jwt.issuer = env.JWT_ISSUER;
  }
  if (env.JWT_AUDIENCE) {
    appOverrides.jwt = appOverrides.jwt || {};
    appOverrides.jwt.audience = env.JWT_AUDIENCE;
  }
  if (env.GUARDIAN_BASE_URL || env.GUARDIAN_API_TIMEOUT_MS) {
    appOverrides.guardian = {};
    if (env.GUARDIAN_BASE_URL) {
      appOverrides.guardian.baseUrl = env.GUARDIAN_BASE_URL;
    }
    if (env.GUARDIAN_API_TIMEOUT_MS) {
      appOverrides.guardian.timeoutMs = parseOptionalInt(
        env.GUARDIAN_API_TIMEOUT_MS,
        'GUARDIAN_API_TIMEOUT_MS'
      );
    }
  }
  if (env.GUARDIAN_TLS_CA_PATH) {
    appOverrides.guardian = appOverrides.guardian || {};
    appOverrides.guardian.caPath = env.GUARDIAN_TLS_CA_PATH;
  }
  if (env.LOG_LEVEL) {
    appOverrides.logging = { level: env.LOG_LEVEL };
  }

  if (env.MONGODB_URI) {
    dbOverrides.uri = env.MONGODB_URI;
  }
  const mongoOptions = {};
  if (env.MONGODB_MAX_POOL_SIZE) {
    mongoOptions.maxPoolSize = parseOptionalInt(env.MONGODB_MAX_POOL_SIZE, 'MONGODB_MAX_POOL_SIZE');
  }
  if (env.MONGODB_MIN_POOL_SIZE) {
    mongoOptions.minPoolSize = parseOptionalInt(env.MONGODB_MIN_POOL_SIZE, 'MONGODB_MIN_POOL_SIZE');
  }
  if (env.MONGODB_SERVER_SELECTION_TIMEOUT_MS) {
    mongoOptions.serverSelectionTimeoutMS = parseOptionalInt(
      env.MONGODB_SERVER_SELECTION_TIMEOUT_MS,
      'MONGODB_SERVER_SELECTION_TIMEOUT_MS'
    );
  }
  if (Object.keys(mongoOptions).length > 0) {
    dbOverrides.options = mongoOptions;
  }

  if (env.TLS_CERT_PATH) {
    tlsOverrides.certPath = env.TLS_CERT_PATH;
  }
  if (env.TLS_KEY_PATH) {
    tlsOverrides.keyPath = env.TLS_KEY_PATH;
  }
  if (env.TLS_CA_PATH) {
    tlsOverrides.caPath = env.TLS_CA_PATH;
  }
  if (env.TLS_REJECT_UNAUTHORIZED !== undefined) {
    tlsOverrides.rejectUnauthorized = parseOptionalBoolean(
      env.TLS_REJECT_UNAUTHORIZED,
      'TLS_REJECT_UNAUTHORIZED'
    );
  }

  return {
    app: appOverrides,
    db: dbOverrides,
    tls: tlsOverrides,
  };
}

module.exports = {
  loadEnvFile,
  buildOverridesFromEnv,
};
