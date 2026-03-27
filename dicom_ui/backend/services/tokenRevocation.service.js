'use strict';

const crypto = require('node:crypto');

const { RevokedToken } = require('../models/revokedToken.model');
const { verifyAccessToken } = require('./jwt.service');

function hashToken(token) {
  if (!token || typeof token !== 'string') {
    throw new Error('JWT token is required');
  }

  return crypto.createHash('sha256').update(token, 'utf8').digest('hex');
}

function resolveTokenExpiryDate(decodedToken) {
  if (!decodedToken || !Number.isInteger(decodedToken.exp)) {
    throw new Error('JWT token expiry is required for revocation');
  }

  return new Date(decodedToken.exp * 1000);
}

async function revokeAccessToken(token, actor = {}) {
  const decodedToken = verifyAccessToken(token);
  const tokenHash = hashToken(token);
  const expiresAt = resolveTokenExpiryDate(decodedToken);

  const record = await RevokedToken.findOneAndUpdate(
    { tokenHash },
    {
      $setOnInsert: {
        tokenHash,
        userId: actor.userId || decodedToken.sub || null,
        username: actor.username || decodedToken.username || null,
        role: actor.role || decodedToken.role || null,
        expiresAt,
        revokedAt: new Date(),
      },
    },
    {
      upsert: true,
      new: true,
      setDefaultsOnInsert: true,
    }
  );

  return {
    tokenHash,
    expiresAt: record.expiresAt,
    revokedAt: record.revokedAt,
  };
}

async function isAccessTokenRevoked(token) {
  const tokenHash = hashToken(token);
  const existing = await RevokedToken.exists({ tokenHash });
  return Boolean(existing);
}

module.exports = {
  hashToken,
  revokeAccessToken,
  isAccessTokenRevoked,
};
