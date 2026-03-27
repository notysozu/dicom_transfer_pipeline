'use strict';

const { USER_ROLES } = require('../models/user.model');

const ROLE_PERMISSIONS = Object.freeze({
  [USER_ROLES.SUPER_ADMIN]: [
    'users:manage',
    'transfers:read',
    'logs:read',
    'system:configure',
    'studies:read',
    'studies:retrieve',
  ],
  [USER_ROLES.ADMIN]: [
    'users:manage',
    'transfers:read',
    'logs:read',
    'studies:read',
    'system:monitor',
  ],
  [USER_ROLES.RADIOLOGIST]: [
    'studies:read',
    'studies:retrieve',
    'transfers:read',
  ],
  [USER_ROLES.TECHNICIAN]: [
    'scans:upload',
    'transfers:read',
    'studies:read',
  ],
  [USER_ROLES.VIEWER]: [
    'dashboard:read',
    'studies:read',
  ],
});

function getRolePermissions(role) {
  return Array.isArray(ROLE_PERMISSIONS[role]) ? [...ROLE_PERMISSIONS[role]] : [];
}

function hasAllPermissions(grantedPermissions, requiredPermissions) {
  const granted = Array.isArray(grantedPermissions) ? grantedPermissions : [];
  const required = Array.isArray(requiredPermissions) ? requiredPermissions : [];

  return required.every((permission) => granted.includes(permission));
}

module.exports = {
  ROLE_PERMISSIONS,
  getRolePermissions,
  hasAllPermissions,
};
