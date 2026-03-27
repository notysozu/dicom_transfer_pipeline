'use strict';

const path = require('node:path');

process.env.JWT_SECRET = process.env.JWT_SECRET || 'super-secure-seed-secret-2026';
process.env.JWT_ISSUER = process.env.JWT_ISSUER || 'dicom_ui_backend';
process.env.JWT_AUDIENCE = process.env.JWT_AUDIENCE || 'dicom_ui_clients';
process.env.JWT_EXPIRES_IN = process.env.JWT_EXPIRES_IN || '1h';

const { buildConfigFromEnv } = require('../config');
const {
  validateTlsFiles,
  buildHttpsServerTlsOptions,
  buildOutboundTlsOptions,
} = require('../config/tls');
const { issueAccessToken, verifyAccessToken } = require('../services/jwt.service');
const { requireAuth } = require('../middleware/auth');
const { requireRoles, requireMinimumRole } = require('../middleware/roles');
const { USER_ROLES } = require('../models/user.model');

function makeRes() {
  return {
    statusCode: 200,
    payload: null,
    status(code) {
      this.statusCode = code;
      return this;
    },
    json(data) {
      this.payload = data;
      return this;
    },
  };
}

async function runSecurityTests() {
  const config = buildConfigFromEnv();
  const projectRoot = path.resolve(__dirname, '..', '..');

  const tls = validateTlsFiles(config.tls, projectRoot);
  if (!tls.certPath || !tls.keyPath || !tls.caPath) {
    throw new Error('TLS path validation failed');
  }

  const httpsOptions = buildHttpsServerTlsOptions(config.tls, projectRoot);
  const outboundOptions = buildOutboundTlsOptions(config.tls, projectRoot);

  if (!httpsOptions.key || !httpsOptions.cert || !httpsOptions.ca) {
    throw new Error('HTTPS TLS options incomplete');
  }
  if (outboundOptions.rejectUnauthorized !== true) {
    throw new Error('Outbound TLS rejectUnauthorized must be true');
  }

  const token = issueAccessToken({
    sub: 'security-test-user',
    username: 'sec_admin',
    role: USER_ROLES.ADMIN,
    permissions: ['users:read', 'users:write'],
  });

  const verified = verifyAccessToken(token);
  if (verified.sub !== 'security-test-user' || verified.role !== USER_ROLES.ADMIN) {
    throw new Error('JWT verify payload mismatch');
  }

  const reqAuth = { headers: { authorization: `Bearer ${token}` } };
  const resAuth = makeRes();
  let authNextCalled = false;
  requireAuth(reqAuth, resAuth, () => {
    authNextCalled = true;
  });
  if (!authNextCalled || !reqAuth.auth || reqAuth.auth.role !== USER_ROLES.ADMIN) {
    throw new Error('requireAuth did not attach auth context');
  }

  const reqRoleAllowed = { auth: reqAuth.auth, params: {} };
  const resRoleAllowed = makeRes();
  let roleNextCalled = false;
  requireRoles(USER_ROLES.ADMIN, USER_ROLES.SUPER_ADMIN)(reqRoleAllowed, resRoleAllowed, () => {
    roleNextCalled = true;
  });
  if (!roleNextCalled) {
    throw new Error('requireRoles denied allowed role');
  }

  const reqRoleDenied = {
    auth: { role: USER_ROLES.VIEWER, userId: 'viewer-1', permissions: [] },
    params: {},
  };
  const resRoleDenied = makeRes();
  requireMinimumRole(USER_ROLES.TECHNICIAN)(reqRoleDenied, resRoleDenied, () => {});
  if (resRoleDenied.statusCode !== 403) {
    throw new Error('requireMinimumRole did not deny low role');
  }

  console.log('[ui-security-test] PASS');
  console.log(`[ui-security-test] tls_cert=${tls.certPath}`);
  console.log(`[ui-security-test] jwt_subject=${verified.sub}`);
  return true;
}

if (require.main === module) {
  runSecurityTests()
    .then(() => process.exit(0))
    .catch((error) => {
      console.error(`[ui-security-test] FAIL reason=${error.message}`);
      process.exit(1);
    });
}

module.exports = {
  runSecurityTests,
};
