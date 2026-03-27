'use strict';

/**
 * Protected transfer route scaffolding with permission enforcement.
 * Transfer monitoring handlers are implemented in Step 68.
 */

const express = require('express');
const { listTransfers } = require('../controllers/transfer.controller');
const { requireAuth } = require('../middleware/auth');
const { requirePermissions } = require('../middleware/roles');

function registerTransferRoutes() {
  const router = express.Router();

  router.use(requireAuth);

  router.get(
    '/',
    requirePermissions('transfers:read'),
    listTransfers
  );

  router.get(
    '/:transferUid',
    requirePermissions('transfers:read'),
    (_req, res) => {
      return res.status(501).json({
        error: 'not_implemented',
        message: 'Transfer detail API will be implemented in Step 68',
      });
    }
  );

  return router;
}

module.exports = registerTransferRoutes;
