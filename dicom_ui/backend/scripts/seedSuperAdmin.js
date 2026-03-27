'use strict';

const { buildConfigFromEnv } = require('../config');
const { connectToDatabase, disconnectFromDatabase } = require('../config/db');
const { User, USER_ROLES } = require('../models/user.model');
const { validatePlainPassword } = require('../services/password.service');

function requireEnv(name) {
  const value = process.env[name];
  if (!value || !String(value).trim()) {
    throw new Error(`${name} is required`);
  }
  return String(value).trim();
}

function optionalEnv(name, defaultValue = '') {
  const value = process.env[name];
  if (value === undefined || value === null) {
    return defaultValue;
  }
  return String(value).trim();
}

async function seedSuperAdmin() {
  const config = buildConfigFromEnv();
  await connectToDatabase(config.db);

  const username = requireEnv('SEED_SUPER_ADMIN_USERNAME');
  const email = requireEnv('SEED_SUPER_ADMIN_EMAIL').toLowerCase();
  const password = requireEnv('SEED_SUPER_ADMIN_PASSWORD');
  validatePlainPassword(password);

  const firstName = optionalEnv('SEED_SUPER_ADMIN_FIRST_NAME', 'Super');
  const lastName = optionalEnv('SEED_SUPER_ADMIN_LAST_NAME', 'Admin');
  const department = optionalEnv('SEED_SUPER_ADMIN_DEPARTMENT', 'Platform Administration');

  const existing = await User.findOne({
    $or: [{ username }, { email }],
  }).select('+passwordHash');

  if (!existing) {
    const created = new User({
      username,
      email,
      role: USER_ROLES.SUPER_ADMIN,
      firstName,
      lastName,
      department,
      isActive: true,
      mustChangePassword: true,
      password,
    });

    await created.save();
    return {
      action: 'created',
      user: created.toSafeObject(),
    };
  }

  existing.username = username;
  existing.email = email;
  existing.role = USER_ROLES.SUPER_ADMIN;
  existing.firstName = firstName;
  existing.lastName = lastName;
  existing.department = department;
  existing.isActive = true;
  existing.mustChangePassword = true;
  existing.password = password;

  await existing.save();
  return {
    action: 'updated',
    user: existing.toSafeObject(),
  };
}

async function main() {
  try {
    const result = await seedSuperAdmin();
    // eslint-disable-next-line no-console
    console.log(`[seed-super-admin] ${result.action}: ${result.user.username} (${result.user.email})`);
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error(`[seed-super-admin] failed: ${error.message}`);
    process.exitCode = 1;
  } finally {
    await disconnectFromDatabase();
  }
}

if (require.main === module) {
  main();
}

module.exports = {
  seedSuperAdmin,
};
