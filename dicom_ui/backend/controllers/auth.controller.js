'use strict';

const crypto = require('node:crypto');

const { AuditLog, AUDIT_CATEGORIES, AUDIT_OUTCOMES, AUDIT_SEVERITIES } = require('../models/auditLog.model');
const { User } = require('../models/user.model');
const { getBearerToken } = require('../middleware/auth');
const { ROLE_PERMISSIONS, getRolePermissions } = require('../services/rbac.service');
const { issueAccessTokenBundle } = require('../services/jwt.service');
const { revokeAccessToken } = require('../services/tokenRevocation.service');

function getClientIp(req) {
  const forwardedFor = req.headers['x-forwarded-for'];
  if (typeof forwardedFor === 'string' && forwardedFor.trim()) {
    return forwardedFor.split(',')[0].trim();
  }
  return req.ip || req.socket?.remoteAddress || null;
}

function normalizeLoginIdentifier(value) {
  if (typeof value !== 'string') {
    return '';
  }
  return value.trim();
}

async function writeAuditLog({
  action,
  outcome,
  severity,
  message,
  actor = {},
  metadata = {},
}) {
  try {
    await AuditLog.create({
      eventId: `auth-${crypto.randomUUID()}`,
      category: AUDIT_CATEGORIES.AUTH,
      action,
      outcome,
      severity,
      message,
      actor,
      metadata,
    });
  } catch (_error) {
    // Audit persistence must not block authentication flow in this step.
  }
}

async function handleLogin(req, res) {
  const usernameOrEmail = normalizeLoginIdentifier(req.body?.username || req.body?.email || req.body?.identifier);
  const password = typeof req.body?.password === 'string' ? req.body.password : '';
  const clientIp = getClientIp(req);
  const userAgent = req.get('user-agent') || null;

  if (!usernameOrEmail || !password) {
    await writeAuditLog({
      action: 'LOGIN',
      outcome: AUDIT_OUTCOMES.FAILURE,
      severity: AUDIT_SEVERITIES.WARN,
      message: 'Login rejected due to missing credentials',
      actor: {
        ipAddress: clientIp,
        userAgent,
      },
      metadata: {
        identifier: usernameOrEmail || null,
      },
    });

    return res.status(400).json({
      error: 'validation_error',
      message: 'username/email and password are required',
    });
  }

  const lookupValue = usernameOrEmail.toLowerCase();
  const user = await User.findOne({
    $or: [
      { username: usernameOrEmail },
      { email: lookupValue },
    ],
  }).select('+passwordHash');

  if (!user) {
    await writeAuditLog({
      action: 'LOGIN',
      outcome: AUDIT_OUTCOMES.FAILURE,
      severity: AUDIT_SEVERITIES.WARN,
      message: 'Login failed because the user account was not found',
      actor: {
        username: usernameOrEmail,
        ipAddress: clientIp,
        userAgent,
      },
      metadata: {
        identifier: usernameOrEmail,
      },
    });

    return res.status(401).json({
      error: 'invalid_credentials',
      message: 'Invalid username/email or password',
    });
  }

  if (!user.isActive) {
    await writeAuditLog({
      action: 'LOGIN',
      outcome: AUDIT_OUTCOMES.DENIED,
      severity: AUDIT_SEVERITIES.WARN,
      message: 'Login denied because the user account is inactive',
      actor: {
        userId: user._id,
        username: user.username,
        role: user.role,
        ipAddress: clientIp,
        userAgent,
      },
    });

    return res.status(403).json({
      error: 'account_inactive',
      message: 'User account is inactive',
    });
  }

  const passwordValid = await user.verifyPassword(password);
  if (!passwordValid) {
    user.failedLoginAttempts += 1;
    await user.save();

    await writeAuditLog({
      action: 'LOGIN',
      outcome: AUDIT_OUTCOMES.FAILURE,
      severity: AUDIT_SEVERITIES.WARN,
      message: 'Login failed because the supplied password was invalid',
      actor: {
        userId: user._id,
        username: user.username,
        role: user.role,
        ipAddress: clientIp,
        userAgent,
      },
      metadata: {
        failedLoginAttempts: user.failedLoginAttempts,
      },
    });

    return res.status(401).json({
      error: 'invalid_credentials',
      message: 'Invalid username/email or password',
    });
  }

  user.failedLoginAttempts = 0;
  user.lastLoginAt = new Date();
  await user.save();

  const safeUser = user.toSafeObject();
  const permissions = getRolePermissions(user.role);
  const tokenBundle = issueAccessTokenBundle({
    sub: safeUser.id,
    username: safeUser.username,
    role: safeUser.role,
    permissions,
  });

  await writeAuditLog({
    action: 'LOGIN',
    outcome: AUDIT_OUTCOMES.SUCCESS,
    severity: AUDIT_SEVERITIES.INFO,
    message: 'Login successful',
    actor: {
      userId: user._id,
      username: user.username,
      role: user.role,
      ipAddress: clientIp,
      userAgent,
    },
    metadata: {
      mustChangePassword: safeUser.mustChangePassword,
    },
  });

  return res.status(200).json({
    tokenType: tokenBundle.tokenType,
    accessToken: tokenBundle.accessToken,
    accessTokenClaims: tokenBundle.accessTokenClaims,
    expiresAt: tokenBundle.expiresAt,
    issuedAt: tokenBundle.issuedAt,
    user: {
      ...safeUser,
      permissions,
    },
  });
}

async function handleLogout(req, res) {
  const token = getBearerToken(req);
  const clientIp = getClientIp(req);
  const userAgent = req.get('user-agent') || null;

  if (!token) {
    return res.status(400).json({
      error: 'validation_error',
      message: 'Bearer token is required for logout',
    });
  }

  try {
    const revocation = await revokeAccessToken(token, {
      userId: req.auth?.userId || null,
      username: req.auth?.username || null,
      role: req.auth?.role || null,
    });

    await writeAuditLog({
      action: 'LOGOUT',
      outcome: AUDIT_OUTCOMES.SUCCESS,
      severity: AUDIT_SEVERITIES.INFO,
      message: 'Logout successful',
      actor: {
        userId: req.auth?.userId || null,
        username: req.auth?.username || null,
        role: req.auth?.role || null,
        ipAddress: clientIp,
        userAgent,
      },
      metadata: {
        revoked: true,
        expiresAt: revocation.expiresAt,
        revokedAt: revocation.revokedAt,
      },
    });

    return res.status(200).json({
      message: 'Logout successful',
      revoked: true,
      expiresAt: revocation.expiresAt,
      revokedAt: revocation.revokedAt,
    });
  } catch (error) {
    await writeAuditLog({
      action: 'LOGOUT',
      outcome: AUDIT_OUTCOMES.FAILURE,
      severity: AUDIT_SEVERITIES.ERROR,
      message: 'Logout failed',
      actor: {
        userId: req.auth?.userId || null,
        username: req.auth?.username || null,
        role: req.auth?.role || null,
        ipAddress: clientIp,
        userAgent,
      },
      metadata: {
        error: error.message,
      },
    });

    return res.status(500).json({
      error: 'logout_failed',
      message: error.message,
    });
  }
}

module.exports = {
  ROLE_PERMISSIONS,
  getRolePermissions,
  handleLogin,
  handleLogout,
};
