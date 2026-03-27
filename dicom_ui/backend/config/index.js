'use strict';

const { buildAppConfig } = require('./app');
const { buildDbConfig } = require('./db');
const { buildTlsConfig } = require('./tls');
const { loadEnvFile, buildOverridesFromEnv } = require('./env');

/**
 * Build full backend configuration object.
 * Step 10 will supply environment-based overrides.
 */
function buildConfig(overrides = {}) {
  return Object.freeze({
    app: buildAppConfig(overrides.app),
    db: buildDbConfig(overrides.db),
    tls: buildTlsConfig(overrides.tls),
  });
}

/**
 * Build backend config from environment variables (and optional explicit overrides).
 */
function buildConfigFromEnv(overrides = {}) {
  loadEnvFile();
  const envOverrides = buildOverridesFromEnv(process.env);
  return buildConfig({
    app: {
      ...(envOverrides.app || {}),
      ...(overrides.app || {}),
    },
    db: {
      ...(envOverrides.db || {}),
      ...(overrides.db || {}),
    },
    tls: {
      ...(envOverrides.tls || {}),
      ...(overrides.tls || {}),
    },
  });
}

module.exports = {
  buildConfig,
  buildConfigFromEnv,
};
