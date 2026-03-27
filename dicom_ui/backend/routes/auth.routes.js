'use strict';

/**
 * Authentication routes with explicit public and protected boundaries.
 * Login/token issuance handlers are implemented in Steps 61-65.
 */

const express = require('express');
const { handleLogin, handleLogout } = require('../controllers/auth.controller');
const { requireAuth } = require('../middleware/auth');

function registerAuthRoutes() {
  const router = express.Router();
  const protectedRouter = express.Router();

  router.post('/login', handleLogin);

  protectedRouter.use(requireAuth);

  protectedRouter.post('/logout', handleLogout);

  protectedRouter.get('/me', (req, res) => {
    return res.status(200).json({
      user: {
        id: req.auth.userId,
        username: req.auth.username,
        role: req.auth.role,
        permissions: req.auth.permissions,
      },
    });
  });

  router.use(protectedRouter);

  return router;
}

module.exports = registerAuthRoutes;
