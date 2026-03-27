'use strict';

const jwt = require('jsonwebtoken');
const { buildConfigFromEnv } = require('../config');

const JWT_ALGORITHM = 'HS256';
const ACCESS_TOKEN_TYPE = 'Bearer';

function getJwtConfig() {
  const config = buildConfigFromEnv();
  const jwtConfig = config.app.jwt;

  if (!jwtConfig.secret || jwtConfig.secret.trim().length < 16) {
    throw new Error('JWT secret must be configured and at least 16 characters long');
  }

  return jwtConfig;
}

function normalizeSubject(subject) {
  if (subject === undefined || subject === null) {
    throw new Error('JWT subject is required');
  }

  const value = String(subject).trim();
  if (!value) {
    throw new Error('JWT subject cannot be empty');
  }

  return value;
}

function buildAccessTokenClaims(payload) {
  const subject = normalizeSubject(payload.sub || payload.userId || payload.id);

  return {
    sub: subject,
    username: payload.username || null,
    role: payload.role || null,
    permissions: Array.isArray(payload.permissions) ? payload.permissions : [],
  };
}

function normalizeDecodedToken(decoded) {
  return {
    sub: decoded.sub || null,
    username: decoded.username || null,
    role: decoded.role || null,
    permissions: Array.isArray(decoded.permissions) ? decoded.permissions : [],
    iss: decoded.iss || null,
    aud: decoded.aud || null,
    iat: Number.isInteger(decoded.iat) ? decoded.iat : null,
    exp: Number.isInteger(decoded.exp) ? decoded.exp : null,
  };
}

function issueAccessToken(payload, overrides = {}) {
  const jwtConfig = getJwtConfig();
  const claims = buildAccessTokenClaims(payload);

  return jwt.sign(claims, jwtConfig.secret, {
    algorithm: JWT_ALGORITHM,
    expiresIn: overrides.expiresIn || jwtConfig.expiresIn,
    issuer: overrides.issuer || jwtConfig.issuer,
    audience: overrides.audience || jwtConfig.audience,
  });
}

function verifyAccessToken(token, overrides = {}) {
  const jwtConfig = getJwtConfig();

  if (!token || typeof token !== 'string') {
    throw new Error('JWT token is required');
  }

  return jwt.verify(token, jwtConfig.secret, {
    algorithms: [JWT_ALGORITHM],
    issuer: overrides.issuer || jwtConfig.issuer,
    audience: overrides.audience || jwtConfig.audience,
  });
}

function decodeAccessToken(token) {
  if (!token || typeof token !== 'string') {
    throw new Error('JWT token is required');
  }

  const decoded = jwt.decode(token, { complete: true });
  if (!decoded) {
    throw new Error('Unable to decode JWT token');
  }

  return decoded;
}

function issueAccessTokenBundle(payload, overrides = {}) {
  const accessToken = issueAccessToken(payload, overrides);
  const decoded = verifyAccessToken(accessToken, overrides);
  const normalizedClaims = normalizeDecodedToken(decoded);

  return {
    tokenType: ACCESS_TOKEN_TYPE,
    accessToken,
    accessTokenClaims: normalizedClaims,
    expiresAt: normalizedClaims.exp,
    issuedAt: normalizedClaims.iat,
  };
}

module.exports = {
  ACCESS_TOKEN_TYPE,
  JWT_ALGORITHM,
  buildAccessTokenClaims,
  getJwtConfig,
  issueAccessToken,
  issueAccessTokenBundle,
  verifyAccessToken,
  decodeAccessToken,
  normalizeDecodedToken,
};
