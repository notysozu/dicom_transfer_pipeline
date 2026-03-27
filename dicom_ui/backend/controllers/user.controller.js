'use strict';

const crypto = require('node:crypto');
const mongoose = require('mongoose');

const { AuditLog, AUDIT_CATEGORIES, AUDIT_OUTCOMES, AUDIT_SEVERITIES } = require('../models/auditLog.model');
const { User, USER_ROLES, USER_ROLE_VALUES } = require('../models/user.model');
const { validatePlainPassword } = require('../services/password.service');

function getClientIp(req) {
  const forwardedFor = req.headers['x-forwarded-for'];
  if (typeof forwardedFor === 'string' && forwardedFor.trim()) {
    return forwardedFor.split(',')[0].trim();
  }
  return req.ip || req.socket?.remoteAddress || null;
}

function normalizeOptionalString(value) {
  if (typeof value !== 'string') {
    return undefined;
  }

  const trimmed = value.trim();
  return trimmed ? trimmed : undefined;
}

function normalizeRequiredString(value, fieldName) {
  const normalized = normalizeOptionalString(value);
  if (!normalized) {
    throw new Error(`${fieldName} is required`);
  }
  return normalized;
}

function normalizeOptionalBoolean(value) {
  if (typeof value === 'boolean') {
    return value;
  }
  if (value === undefined || value === null || value === '') {
    return undefined;
  }
  if (value === 'true') {
    return true;
  }
  if (value === 'false') {
    return false;
  }
  throw new Error('Boolean fields must be true or false');
}

function normalizeLimit(value, fallback = 100) {
  if (value === undefined || value === null || value === '') {
    return fallback;
  }

  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed < 1 || parsed > 1000) {
    throw new Error('limit must be an integer between 1 and 1000');
  }

  return parsed;
}

function normalizeRole(value, { required = false } = {}) {
  if (value === undefined || value === null || value === '') {
    if (required) {
      throw new Error('role is required');
    }
    return undefined;
  }

  const normalized = String(value).trim().toUpperCase();
  if (!USER_ROLE_VALUES.includes(normalized)) {
    throw new Error(`role must be one of: ${USER_ROLE_VALUES.join(', ')}`);
  }

  return normalized;
}

function ensureValidObjectId(userId, fieldName = 'userId') {
  const normalized = typeof userId === 'string' ? userId.trim() : String(userId || '').trim();

  if (!mongoose.Types.ObjectId.isValid(normalized)) {
    throw new Error(`${fieldName} must be a valid identifier`);
  }

  return normalized;
}

function assertManageableRole(actorRole, targetRole) {
  if (actorRole === USER_ROLES.ADMIN && targetRole === USER_ROLES.SUPER_ADMIN) {
    throw new Error('ADMIN cannot manage SUPER_ADMIN users');
  }
}

async function writeAuditLog({
  action,
  outcome,
  severity,
  message,
  actor = {},
  target = {},
  metadata = {},
}) {
  try {
    await AuditLog.create({
      eventId: `users-${crypto.randomUUID()}`,
      category: AUDIT_CATEGORIES.USER_MANAGEMENT,
      action,
      outcome,
      severity,
      message,
      actor,
      target,
      metadata,
    });
  } catch (_error) {
    // Audit persistence must not block user management flow in this step.
  }
}

function buildAuditActor(req) {
  return {
    userId: req.auth?.userId || null,
    username: req.auth?.username || null,
    role: req.auth?.role || null,
    ipAddress: getClientIp(req),
    userAgent: req.get('user-agent') || null,
  };
}

function buildUserListQuery(req) {
  return {
    role: normalizeRole(req.query?.role),
    isActive: normalizeOptionalBoolean(req.query?.isActive),
    limit: normalizeLimit(req.query?.limit),
  };
}

function buildCreateUserPayload(body) {
  const password = validatePlainPassword(normalizeRequiredString(body?.password, 'password'));

  return {
    username: normalizeRequiredString(body?.username, 'username'),
    email: normalizeRequiredString(body?.email, 'email').toLowerCase(),
    password,
    role: normalizeRole(body?.role, { required: true }),
    firstName: normalizeOptionalString(body?.firstName),
    lastName: normalizeOptionalString(body?.lastName),
    department: normalizeOptionalString(body?.department),
    isActive: normalizeOptionalBoolean(body?.isActive),
    mustChangePassword: normalizeOptionalBoolean(body?.mustChangePassword),
  };
}

function buildUpdateUserPayload(body) {
  const payload = {};

  if (body?.username !== undefined) {
    payload.username = normalizeRequiredString(body.username, 'username');
  }
  if (body?.email !== undefined) {
    payload.email = normalizeRequiredString(body.email, 'email').toLowerCase();
  }
  if (body?.role !== undefined) {
    payload.role = normalizeRole(body.role, { required: true });
  }
  if (body?.firstName !== undefined) {
    payload.firstName = normalizeOptionalString(body.firstName) || null;
  }
  if (body?.lastName !== undefined) {
    payload.lastName = normalizeOptionalString(body.lastName) || null;
  }
  if (body?.department !== undefined) {
    payload.department = normalizeOptionalString(body.department) || null;
  }
  if (body?.isActive !== undefined) {
    payload.isActive = normalizeOptionalBoolean(body.isActive);
  }
  if (body?.mustChangePassword !== undefined) {
    payload.mustChangePassword = normalizeOptionalBoolean(body.mustChangePassword);
  }
  if (body?.password !== undefined) {
    payload.password = validatePlainPassword(normalizeRequiredString(body.password, 'password'));
  }

  if (Object.keys(payload).length === 0) {
    throw new Error('At least one updatable field is required');
  }

  return payload;
}

async function listUsers(req, res) {
  let query;

  try {
    query = buildUserListQuery(req);
  } catch (error) {
    return res.status(400).json({
      error: 'validation_error',
      message: error.message,
    });
  }

  const mongoQuery = {};
  if (query.role) {
    mongoQuery.role = query.role;
  }
  if (typeof query.isActive === 'boolean') {
    mongoQuery.isActive = query.isActive;
  }

  const actorRole = req.auth?.role || null;
  if (actorRole === USER_ROLES.ADMIN) {
    mongoQuery.role = { ...(mongoQuery.role ? { $eq: mongoQuery.role } : { $ne: USER_ROLES.SUPER_ADMIN }) };
    if (mongoQuery.role.$eq === USER_ROLES.SUPER_ADMIN) {
      return res.status(403).json({
        error: 'forbidden',
        message: 'ADMIN cannot view SUPER_ADMIN users',
      });
    }
  }

  const users = await User.find(mongoQuery)
    .sort({ createdAt: -1 })
    .limit(query.limit);

  return res.status(200).json({
    count: users.length,
    filters: query,
    users: users.map((user) => user.toSafeObject()),
  });
}

async function createUser(req, res) {
  let payload;

  try {
    payload = buildCreateUserPayload(req.body);
    assertManageableRole(req.auth?.role, payload.role);
  } catch (error) {
    return res.status(error.message.includes('cannot manage') ? 403 : 400).json({
      error: error.message.includes('cannot manage') ? 'forbidden' : 'validation_error',
      message: error.message,
    });
  }

  const existing = await User.findOne({
    $or: [
      { username: payload.username },
      { email: payload.email },
    ],
  });

  if (existing) {
    return res.status(409).json({
      error: 'conflict',
      message: 'A user with that username or email already exists',
    });
  }

  const user = new User({
    username: payload.username,
    email: payload.email,
    role: payload.role,
    firstName: payload.firstName,
    lastName: payload.lastName,
    department: payload.department,
    isActive: typeof payload.isActive === 'boolean' ? payload.isActive : true,
    mustChangePassword:
      typeof payload.mustChangePassword === 'boolean' ? payload.mustChangePassword : false,
    password: payload.password,
    createdBy: req.auth?.userId || null,
    updatedBy: req.auth?.userId || null,
  });

  await user.save();

  await writeAuditLog({
    action: 'USER_CREATE',
    outcome: AUDIT_OUTCOMES.SUCCESS,
    severity: AUDIT_SEVERITIES.INFO,
    message: 'User created successfully',
    actor: buildAuditActor(req),
    target: {
      resourceType: 'USER',
      resourceId: user._id.toString(),
    },
    metadata: {
      role: user.role,
      username: user.username,
    },
  });

  return res.status(201).json({
    user: user.toSafeObject(),
  });
}

async function updateUser(req, res) {
  let normalizedUserId;

  try {
    normalizedUserId = ensureValidObjectId(req.params?.userId);
  } catch (error) {
    return res.status(400).json({
      error: 'validation_error',
      message: error.message,
    });
  }

  let payload;
  try {
    payload = buildUpdateUserPayload(req.body);
  } catch (error) {
    return res.status(400).json({
      error: 'validation_error',
      message: error.message,
    });
  }

  const user = await User.findById(normalizedUserId).select('+passwordHash');
  if (!user) {
    return res.status(404).json({
      error: 'not_found',
      message: 'User not found',
    });
  }

  try {
    assertManageableRole(req.auth?.role, user.role);
    if (payload.role) {
      assertManageableRole(req.auth?.role, payload.role);
    }
  } catch (error) {
    return res.status(403).json({
      error: 'forbidden',
      message: error.message,
    });
  }

  if (payload.username && payload.username !== user.username) {
    const existingUsername = await User.findOne({ username: payload.username, _id: { $ne: user._id } });
    if (existingUsername) {
      return res.status(409).json({
        error: 'conflict',
        message: 'A user with that username already exists',
      });
    }
    user.username = payload.username;
  }

  if (payload.email && payload.email !== user.email) {
    const existingEmail = await User.findOne({ email: payload.email, _id: { $ne: user._id } });
    if (existingEmail) {
      return res.status(409).json({
        error: 'conflict',
        message: 'A user with that email already exists',
      });
    }
    user.email = payload.email;
  }

  if (payload.role) {
    user.role = payload.role;
  }
  if (payload.firstName !== undefined) {
    user.firstName = payload.firstName;
  }
  if (payload.lastName !== undefined) {
    user.lastName = payload.lastName;
  }
  if (payload.department !== undefined) {
    user.department = payload.department;
  }
  if (typeof payload.isActive === 'boolean') {
    user.isActive = payload.isActive;
  }
  if (typeof payload.mustChangePassword === 'boolean') {
    user.mustChangePassword = payload.mustChangePassword;
  }
  if (payload.password) {
    user.password = payload.password;
    user.failedLoginAttempts = 0;
  }

  user.updatedBy = req.auth?.userId || null;
  await user.save();

  await writeAuditLog({
    action: 'USER_UPDATE',
    outcome: AUDIT_OUTCOMES.SUCCESS,
    severity: AUDIT_SEVERITIES.INFO,
    message: 'User updated successfully',
    actor: buildAuditActor(req),
    target: {
      resourceType: 'USER',
      resourceId: user._id.toString(),
    },
    metadata: {
      role: user.role,
      username: user.username,
      passwordChanged: Boolean(payload.password),
    },
  });

  return res.status(200).json({
    user: user.toSafeObject(),
  });
}

module.exports = {
  buildUserListQuery,
  buildCreateUserPayload,
  buildUpdateUserPayload,
  listUsers,
  createUser,
  updateUser,
};
