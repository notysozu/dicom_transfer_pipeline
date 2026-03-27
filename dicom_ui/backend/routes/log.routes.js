'use strict';

/**
 * Protected log route scaffolding with permission enforcement.
 * Log retrieval handlers are implemented in Step 69.
 */

const express = require('express');
const { listLogs } = require('../controllers/log.controller');
const { requireAuth } = require('../middleware/auth');
const { requirePermissions } = require('../middleware/roles');

function registerLogRoutes() {
  const router = express.Router();

  router.use(requireAuth);

  router.get(
    '/',
    requirePermissions('logs:read'),
    listLogs
  );

  return router;
}

module.exports = registerLogRoutes;
