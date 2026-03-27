'use strict';

/**
 * MongoDB configuration shape.
 * Step 15 adds connection lifecycle helpers.
 */

const mongoose = require('mongoose');

const DEFAULT_DB_CONFIG = Object.freeze({
  uri: 'mongodb://127.0.0.1:27017/dicom_ui',
  options: Object.freeze({
    maxPoolSize: 10,
    minPoolSize: 2,
    serverSelectionTimeoutMS: 5000,
  }),
});

function buildDbConfig(overrides = {}) {
  return Object.freeze({
    uri: overrides.uri || DEFAULT_DB_CONFIG.uri,
    options: Object.freeze({
      ...DEFAULT_DB_CONFIG.options,
      ...(overrides.options || {}),
    }),
  });
}

function normalizeDbOptions(options = {}) {
  return {
    maxPoolSize: options.maxPoolSize,
    minPoolSize: options.minPoolSize,
    serverSelectionTimeoutMS: options.serverSelectionTimeoutMS,
  };
}

function getConnectionState() {
  return mongoose.connection.readyState;
}

function isConnected() {
  return getConnectionState() === 1;
}

function attachConnectionLogging() {
  if (mongoose.connection.listeners('connected').length > 0) {
    return;
  }

  mongoose.connection.on('connected', () => {
    // eslint-disable-next-line no-console
    console.info('[db] MongoDB connected');
  });

  mongoose.connection.on('disconnected', () => {
    // eslint-disable-next-line no-console
    console.warn('[db] MongoDB disconnected');
  });

  mongoose.connection.on('error', (error) => {
    // eslint-disable-next-line no-console
    console.error('[db] MongoDB error:', error.message);
  });
}

async function connectToDatabase(dbConfig) {
  if (!dbConfig || !dbConfig.uri) {
    throw new Error('dbConfig.uri is required');
  }

  if (isConnected()) {
    return mongoose.connection;
  }

  attachConnectionLogging();
  const options = normalizeDbOptions(dbConfig.options);
  await mongoose.connect(dbConfig.uri, options);
  return mongoose.connection;
}

async function disconnectFromDatabase() {
  if (getConnectionState() === 0) {
    return;
  }
  await mongoose.disconnect();
}

async function checkDatabaseConnection() {
  if (!isConnected()) {
    return false;
  }

  try {
    await mongoose.connection.db.admin().ping();
    return true;
  } catch (_error) {
    return false;
  }
}

module.exports = {
  DEFAULT_DB_CONFIG,
  buildDbConfig,
  connectToDatabase,
  disconnectFromDatabase,
  checkDatabaseConnection,
  getConnectionState,
  isConnected,
};
