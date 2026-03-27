'use strict';

/**
 * Protected user management route scaffolding with permission enforcement.
 * User management handlers are implemented in Step 70.
 */

const express = require('express');
const { createUser, listUsers, updateUser } = require('../controllers/user.controller');
const { requireAuth } = require('../middleware/auth');
const { requirePermissions } = require('../middleware/roles');

function registerUserRoutes() {
  const router = express.Router();

  router.use(requireAuth);

  router.get(
    '/',
    requirePermissions('users:manage'),
    listUsers
  );

  router.post(
    '/',
    requirePermissions('users:manage'),
    createUser
  );

  router.patch(
    '/:userId',
    requirePermissions('users:manage'),
    updateUser
  );

  return router;
}

module.exports = registerUserRoutes;
