'use strict';

/**
 * Protected study route scaffolding with permission enforcement.
 * Study business handlers are implemented in Step 67.
 */

const express = require('express');
const { listStudies } = require('../controllers/study.controller');
const { requireAuth } = require('../middleware/auth');
const { requirePermissions } = require('../middleware/roles');

function registerStudyRoutes() {
  const router = express.Router();

  router.use(requireAuth);

  router.get(
    '/',
    requirePermissions('studies:read'),
    listStudies
  );

  router.post(
    '/retrieve',
    requirePermissions('studies:retrieve'),
    (_req, res) => {
      return res.status(501).json({
        error: 'not_implemented',
        message: 'Study retrieval trigger will be implemented in Step 67',
      });
    }
  );

  return router;
}

module.exports = registerStudyRoutes;
