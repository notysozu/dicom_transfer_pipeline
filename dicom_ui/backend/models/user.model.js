'use strict';

/**
 * User schema and model for dicom_ui backend.
 * Password hashing is implemented in Step 17.
 */

const mongoose = require('mongoose');
const { hashPassword, verifyPassword } = require('../services/password.service');

const USER_ROLES = Object.freeze({
  SUPER_ADMIN: 'SUPER_ADMIN',
  ADMIN: 'ADMIN',
  RADIOLOGIST: 'RADIOLOGIST',
  TECHNICIAN: 'TECHNICIAN',
  VIEWER: 'VIEWER',
});

const USER_ROLE_VALUES = Object.freeze(Object.values(USER_ROLES));

const userSchema = new mongoose.Schema(
  {
    username: {
      type: String,
      required: true,
      trim: true,
      minlength: 3,
      maxlength: 64,
      unique: true,
      index: true,
    },
    email: {
      type: String,
      required: true,
      trim: true,
      lowercase: true,
      maxlength: 254,
      unique: true,
      index: true,
    },
    passwordHash: {
      type: String,
      required: true,
      minlength: 20,
      select: false,
    },
    role: {
      type: String,
      enum: USER_ROLE_VALUES,
      required: true,
      default: USER_ROLES.VIEWER,
      index: true,
    },
    firstName: {
      type: String,
      trim: true,
      maxlength: 64,
    },
    lastName: {
      type: String,
      trim: true,
      maxlength: 64,
    },
    department: {
      type: String,
      trim: true,
      maxlength: 128,
    },
    isActive: {
      type: Boolean,
      default: true,
      index: true,
    },
    mustChangePassword: {
      type: Boolean,
      default: false,
    },
    failedLoginAttempts: {
      type: Number,
      default: 0,
      min: 0,
    },
    lastLoginAt: {
      type: Date,
      default: null,
    },
    createdBy: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'User',
      default: null,
    },
    updatedBy: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'User',
      default: null,
    },
  },
  {
    timestamps: true,
    versionKey: false,
    collection: 'users',
  }
);

userSchema.index({ role: 1, isActive: 1 });
userSchema.index({ createdAt: -1 });

userSchema.virtual('password')
  .set(function setPasswordVirtual(password) {
    this._plainPassword = password;
  })
  .get(function getPasswordVirtual() {
    return this._plainPassword;
  });

userSchema.pre('validate', async function hashIncomingPassword() {
  if (this._plainPassword) {
    this.passwordHash = await hashPassword(this._plainPassword);
  }
});

userSchema.methods.setPassword = async function setPassword(password) {
  this.passwordHash = await hashPassword(password);
  this._plainPassword = undefined;
};

userSchema.methods.verifyPassword = async function verifyUserPassword(password) {
  return verifyPassword(password, this.passwordHash);
};

userSchema.methods.toSafeObject = function toSafeObject() {
  return {
    id: this._id.toString(),
    username: this.username,
    email: this.email,
    role: this.role,
    firstName: this.firstName || null,
    lastName: this.lastName || null,
    department: this.department || null,
    isActive: this.isActive,
    mustChangePassword: this.mustChangePassword,
    failedLoginAttempts: this.failedLoginAttempts,
    lastLoginAt: this.lastLoginAt,
    createdAt: this.createdAt,
    updatedAt: this.updatedAt,
  };
};

const User = mongoose.models.User || mongoose.model('User', userSchema);

module.exports = {
  User,
  userSchema,
  USER_ROLES,
  USER_ROLE_VALUES,
};
