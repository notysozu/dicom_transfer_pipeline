'use strict';

/**
 * TLS configuration shape for backend HTTPS and outbound validation.
 * Step 23 adds TLS file validation and option builders.
 */

const fs = require('node:fs');
const path = require('node:path');

const PROJECT_ROOT = path.resolve(__dirname, '../..');

const DEFAULT_TLS_CONFIG = Object.freeze({
  certPath: './backend/certificates/server.pem',
  keyPath: './backend/certificates/key.pem',
  caPath: './backend/certificates/ca.pem',
  rejectUnauthorized: true,
});

function buildTlsConfig(overrides = {}) {
  return Object.freeze({
    certPath: overrides.certPath || DEFAULT_TLS_CONFIG.certPath,
    keyPath: overrides.keyPath || DEFAULT_TLS_CONFIG.keyPath,
    caPath: overrides.caPath || DEFAULT_TLS_CONFIG.caPath,
    rejectUnauthorized:
      typeof overrides.rejectUnauthorized === 'boolean'
        ? overrides.rejectUnauthorized
        : DEFAULT_TLS_CONFIG.rejectUnauthorized,
  });
}

function resolveProjectPath(filePath, cwd = process.cwd()) {
  if (path.isAbsolute(filePath)) {
    return filePath;
  }

  return path.resolve(PROJECT_ROOT, filePath);
}

function resolveTlsConfigPaths(tlsConfig = DEFAULT_TLS_CONFIG, cwd = process.cwd()) {
  return Object.freeze({
    certPath: resolveProjectPath(tlsConfig.certPath, cwd),
    keyPath: resolveProjectPath(tlsConfig.keyPath, cwd),
    caPath: resolveProjectPath(tlsConfig.caPath, cwd),
    rejectUnauthorized: tlsConfig.rejectUnauthorized,
  });
}

function validateTlsFiles(tlsConfig = DEFAULT_TLS_CONFIG, cwd = process.cwd()) {
  const resolved = resolveTlsConfigPaths(tlsConfig, cwd);
  const missing = [];
  const invalid = [];

  for (const filePath of [resolved.certPath, resolved.keyPath, resolved.caPath]) {
    if (!fs.existsSync(filePath)) {
      missing.push(filePath);
      continue;
    }

    const stat = fs.statSync(filePath);
    if (!stat.isFile()) {
      invalid.push(`${filePath} is not a file`);
      continue;
    }
    if (stat.size <= 0) {
      invalid.push(`${filePath} is empty`);
    }
  }

  if (missing.length || invalid.length) {
    const errorParts = [];
    if (missing.length) {
      errorParts.push(`missing=[${missing.join(', ')}]`);
    }
    if (invalid.length) {
      errorParts.push(`invalid=[${invalid.join(', ')}]`);
    }
    throw new Error(`TLS file validation failed: ${errorParts.join(' ')}`);
  }

  return resolved;
}

function loadTlsMaterial(tlsConfig = DEFAULT_TLS_CONFIG, cwd = process.cwd()) {
  const resolved = validateTlsFiles(tlsConfig, cwd);

  return Object.freeze({
    cert: fs.readFileSync(resolved.certPath),
    key: fs.readFileSync(resolved.keyPath),
    ca: fs.readFileSync(resolved.caPath),
    rejectUnauthorized: resolved.rejectUnauthorized,
    paths: resolved,
  });
}

function buildHttpsServerTlsOptions(tlsConfig = DEFAULT_TLS_CONFIG, cwd = process.cwd()) {
  const tlsMaterial = loadTlsMaterial(tlsConfig, cwd);
  return Object.freeze({
    key: tlsMaterial.key,
    cert: tlsMaterial.cert,
    ca: tlsMaterial.ca,
    requestCert: false,
    rejectUnauthorized: tlsMaterial.rejectUnauthorized,
    minVersion: 'TLSv1.2',
    honorCipherOrder: true,
  });
}

function buildOutboundTlsOptions(tlsConfig = DEFAULT_TLS_CONFIG, cwd = process.cwd()) {
  const tlsMaterial = loadTlsMaterial(tlsConfig, cwd);
  return Object.freeze({
    ca: tlsMaterial.ca,
    cert: tlsMaterial.cert,
    key: tlsMaterial.key,
    rejectUnauthorized: tlsMaterial.rejectUnauthorized,
    minVersion: 'TLSv1.2',
  });
}

function tlsDiagnostics(tlsConfig = DEFAULT_TLS_CONFIG, cwd = process.cwd()) {
  const resolved = validateTlsFiles(tlsConfig, cwd);
  return Object.freeze({
    certPath: resolved.certPath,
    keyPath: resolved.keyPath,
    caPath: resolved.caPath,
    rejectUnauthorized: resolved.rejectUnauthorized,
    certSize: fs.statSync(resolved.certPath).size,
    keySize: fs.statSync(resolved.keyPath).size,
    caSize: fs.statSync(resolved.caPath).size,
  });
}

module.exports = {
  DEFAULT_TLS_CONFIG,
  buildTlsConfig,
  resolveProjectPath,
  resolveTlsConfigPaths,
  validateTlsFiles,
  loadTlsMaterial,
  buildHttpsServerTlsOptions,
  buildOutboundTlsOptions,
  tlsDiagnostics,
};
