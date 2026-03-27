'use strict';

const mongoose = require('mongoose');

const revokedTokenSchema = new mongoose.Schema(
  {
    tokenHash: {
      type: String,
      required: true,
      unique: true,
      index: true,
      trim: true,
      minlength: 64,
      maxlength: 64,
    },
    userId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'User',
      default: null,
      index: true,
    },
    username: {
      type: String,
      trim: true,
      maxlength: 64,
      default: null,
    },
    role: {
      type: String,
      trim: true,
      maxlength: 32,
      default: null,
    },
    expiresAt: {
      type: Date,
      required: true,
    },
    revokedAt: {
      type: Date,
      required: true,
      default: Date.now,
      index: true,
    },
  },
  {
    timestamps: true,
    versionKey: false,
    collection: 'revoked_tokens',
  }
);

revokedTokenSchema.index({ expiresAt: 1 }, { expireAfterSeconds: 0 });
revokedTokenSchema.index({ userId: 1, revokedAt: -1 });

const RevokedToken =
  mongoose.models.RevokedToken || mongoose.model('RevokedToken', revokedTokenSchema);

module.exports = {
  RevokedToken,
  revokedTokenSchema,
};
