'use strict';

/**
 * JWT authentication middleware (Step 27).
 */

const { isAccessTokenRevoked } = require('../services/tokenRevocation.service');
const { verifyAccessToken } = require('../services/jwt.service');

function getBearerToken(req) {
  const rawHeader = req.headers.authorization || req.headers.Authorization;
  if (!rawHeader || typeof rawHeader !== 'string') {
    return null;
  }

  const [scheme, token] = rawHeader.trim().split(/\s+/, 2);
  if (!scheme || scheme.toLowerCase() !== 'bearer' || !token) {
    return null;
  }

  return token;
}

function buildAuthContext(decodedToken) {
  return {
    token: decodedToken,
    userId: decodedToken.sub,
    username: decodedToken.username || null,
    role: decodedToken.role || null,
    permissions: Array.isArray(decodedToken.permissions) ? decodedToken.permissions : [],
  };
}

function unauthorized(res, message = 'Authentication required') {
  return res.status(401).json({
    error: 'unauthorized',
    message,
  });
}

async function requireAuth(req, res, next) {
  const token = getBearerToken(req);
  if (!token) {
    return unauthorized(res, 'Bearer token is missing');
  }

  try {
    const revoked = await isAccessTokenRevoked(token);
    if (revoked) {
      return unauthorized(res, 'Token has been revoked');
    }

    const decoded = verifyAccessToken(token);
    req.auth = buildAuthContext(decoded);
    return next();
  } catch (error) {
    return unauthorized(res, `Invalid token: ${error.message}`);
  }
}

async function optionalAuth(req, _res, next) {
  const token = getBearerToken(req);
  if (!token) {
    return next();
  }

  try {
    const revoked = await isAccessTokenRevoked(token);
    if (revoked) {
      req.auth = null;
      return next();
    }

    const decoded = verifyAccessToken(token);
    req.auth = buildAuthContext(decoded);
  } catch (_error) {
    req.auth = null;
  }

  return next();
}

module.exports = {
  getBearerToken,
  requireAuth,
  optionalAuth,
};
