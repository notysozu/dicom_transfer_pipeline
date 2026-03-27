'use strict';

/**
 * Role-based access control middleware (Step 28).
 */

const { USER_ROLES, USER_ROLE_VALUES } = require('../models/user.model');

const ROLE_PRIORITY = Object.freeze({
  [USER_ROLES.SUPER_ADMIN]: 500,
  [USER_ROLES.ADMIN]: 400,
  [USER_ROLES.RADIOLOGIST]: 300,
  [USER_ROLES.TECHNICIAN]: 200,
  [USER_ROLES.VIEWER]: 100,
});

function forbidden(res, message = 'Forbidden') {
  return res.status(403).json({
    error: 'forbidden',
    message,
  });
}

function getAuthRole(req) {
  return req?.auth?.role || null;
}

function ensureRoleValid(role) {
  if (!USER_ROLE_VALUES.includes(role)) {
    throw new Error(`Unknown role: ${role}`);
  }
}

function requireRoles(...allowedRoles) {
  const resolvedAllowed = [...new Set(allowedRoles)];
  resolvedAllowed.forEach(ensureRoleValid);

  return function roleMiddleware(req, res, next) {
    if (!req.auth) {
      return forbidden(res, 'Authentication context is missing');
    }

    const role = getAuthRole(req);
    if (!role || !resolvedAllowed.includes(role)) {
      return forbidden(res, `Role ${role || '<none>'} is not permitted`);
    }

    return next();
  };
}

function requireMinimumRole(minimumRole) {
  ensureRoleValid(minimumRole);
  const minimumPriority = ROLE_PRIORITY[minimumRole];

  return function minimumRoleMiddleware(req, res, next) {
    if (!req.auth) {
      return forbidden(res, 'Authentication context is missing');
    }

    const role = getAuthRole(req);
    if (!role || ROLE_PRIORITY[role] < minimumPriority) {
      return forbidden(res, `Role ${role || '<none>'} does not meet minimum ${minimumRole}`);
    }

    return next();
  };
}

function requirePermissions(...requiredPermissions) {
  const required = [...new Set(requiredPermissions)].filter(Boolean);

  return function permissionMiddleware(req, res, next) {
    if (!req.auth) {
      return forbidden(res, 'Authentication context is missing');
    }

    const granted = Array.isArray(req.auth.permissions) ? req.auth.permissions : [];
    const missing = required.filter((permission) => !granted.includes(permission));

    if (missing.length > 0) {
      return forbidden(res, `Missing permissions: ${missing.join(', ')}`);
    }

    return next();
  };
}

function requireSelfOrRoles(roles, userIdParam = 'userId') {
  const roleGuard = requireRoles(...roles);

  return function selfOrRoleMiddleware(req, res, next) {
    if (!req.auth) {
      return forbidden(res, 'Authentication context is missing');
    }

    const targetUserId = req.params?.[userIdParam];
    if (targetUserId && req.auth.userId && String(targetUserId) === String(req.auth.userId)) {
      return next();
    }

    return roleGuard(req, res, next);
  };
}

module.exports = {
  ROLE_PRIORITY,
  requireRoles,
  requireMinimumRole,
  requirePermissions,
  requireSelfOrRoles,
};
