'use strict';

const bcrypt = require('bcrypt');

const DEFAULT_BCRYPT_ROUNDS = 12;
const MIN_BCRYPT_ROUNDS = 10;
const MAX_BCRYPT_ROUNDS = 15;
const MIN_PASSWORD_LENGTH = 12;
const MAX_PASSWORD_LENGTH = 128;

function getBcryptRounds() {
  const raw = process.env.BCRYPT_SALT_ROUNDS;
  if (!raw) {
    return DEFAULT_BCRYPT_ROUNDS;
  }

  const parsed = Number(raw);
  if (!Number.isInteger(parsed)) {
    throw new Error('BCRYPT_SALT_ROUNDS must be an integer');
  }

  if (parsed < MIN_BCRYPT_ROUNDS || parsed > MAX_BCRYPT_ROUNDS) {
    throw new Error(
      `BCRYPT_SALT_ROUNDS must be between ${MIN_BCRYPT_ROUNDS} and ${MAX_BCRYPT_ROUNDS}`
    );
  }

  return parsed;
}

function validatePlainPassword(password) {
  if (typeof password !== 'string') {
    throw new Error('Password must be a string');
  }

  const normalized = password.trim();
  if (normalized.length < MIN_PASSWORD_LENGTH) {
    throw new Error(`Password must be at least ${MIN_PASSWORD_LENGTH} characters`);
  }

  if (normalized.length > MAX_PASSWORD_LENGTH) {
    throw new Error(`Password must be at most ${MAX_PASSWORD_LENGTH} characters`);
  }

  return normalized;
}

async function hashPassword(plainPassword) {
  const normalized = validatePlainPassword(plainPassword);
  const rounds = getBcryptRounds();
  return bcrypt.hash(normalized, rounds);
}

async function verifyPassword(plainPassword, passwordHash) {
  if (!passwordHash || typeof passwordHash !== 'string') {
    return false;
  }

  const normalized = validatePlainPassword(plainPassword);
  return bcrypt.compare(normalized, passwordHash);
}

module.exports = {
  DEFAULT_BCRYPT_ROUNDS,
  MIN_BCRYPT_ROUNDS,
  MAX_BCRYPT_ROUNDS,
  MIN_PASSWORD_LENGTH,
  MAX_PASSWORD_LENGTH,
  getBcryptRounds,
  validatePlainPassword,
  hashPassword,
  verifyPassword,
};
