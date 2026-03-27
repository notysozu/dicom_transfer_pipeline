'use strict';

/**
 * Audit log schema for security, compliance, and operational traceability.
 */

const mongoose = require('mongoose');

const AUDIT_CATEGORIES = Object.freeze({
  AUTH: 'AUTH',
  ACCESS_CONTROL: 'ACCESS_CONTROL',
  USER_MANAGEMENT: 'USER_MANAGEMENT',
  STUDY: 'STUDY',
  TRANSFER: 'TRANSFER',
  SYSTEM: 'SYSTEM',
});

const AUDIT_OUTCOMES = Object.freeze({
  SUCCESS: 'SUCCESS',
  FAILURE: 'FAILURE',
  DENIED: 'DENIED',
});

const AUDIT_SEVERITIES = Object.freeze({
  INFO: 'INFO',
  WARN: 'WARN',
  ERROR: 'ERROR',
  CRITICAL: 'CRITICAL',
});

const auditLogSchema = new mongoose.Schema(
  {
    eventId: {
      type: String,
      required: true,
      unique: true,
      index: true,
      trim: true,
      maxlength: 128,
    },
    category: {
      type: String,
      required: true,
      enum: Object.values(AUDIT_CATEGORIES),
      index: true,
    },
    action: {
      type: String,
      required: true,
      trim: true,
      maxlength: 128,
      index: true,
    },
    outcome: {
      type: String,
      required: true,
      enum: Object.values(AUDIT_OUTCOMES),
      index: true,
    },
    severity: {
      type: String,
      required: true,
      enum: Object.values(AUDIT_SEVERITIES),
      default: AUDIT_SEVERITIES.INFO,
      index: true,
    },
    message: {
      type: String,
      required: true,
      trim: true,
      maxlength: 1024,
    },
    actor: {
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
      ipAddress: {
        type: String,
        trim: true,
        maxlength: 64,
        default: null,
      },
      userAgent: {
        type: String,
        trim: true,
        maxlength: 512,
        default: null,
      },
    },
    target: {
      resourceType: {
        type: String,
        trim: true,
        maxlength: 64,
        default: null,
      },
      resourceId: {
        type: String,
        trim: true,
        maxlength: 128,
        default: null,
      },
      studyInstanceUid: {
        type: String,
        trim: true,
        maxlength: 128,
        default: null,
      },
      transferUid: {
        type: String,
        trim: true,
        maxlength: 128,
        default: null,
      },
    },
    correlationId: {
      type: String,
      trim: true,
      maxlength: 128,
      default: null,
      index: true,
    },
    requestId: {
      type: String,
      trim: true,
      maxlength: 128,
      default: null,
      index: true,
    },
    metadata: {
      type: mongoose.Schema.Types.Mixed,
      default: {},
    },
    occurredAt: {
      type: Date,
      required: true,
      default: Date.now,
      index: true,
      immutable: true,
    },
  },
  {
    timestamps: true,
    versionKey: false,
    collection: 'audit_logs',
  }
);

auditLogSchema.index({ occurredAt: -1, category: 1 });
auditLogSchema.index({ 'actor.userId': 1, occurredAt: -1 });
auditLogSchema.index({ outcome: 1, severity: 1, occurredAt: -1 });
auditLogSchema.index({ 'target.studyInstanceUid': 1, occurredAt: -1 });
auditLogSchema.index({ 'target.transferUid': 1, occurredAt: -1 });

auditLogSchema.methods.toSafeObject = function toSafeObject() {
  return {
    id: this._id.toString(),
    eventId: this.eventId,
    category: this.category,
    action: this.action,
    outcome: this.outcome,
    severity: this.severity,
    message: this.message,
    actor: this.actor,
    target: this.target,
    correlationId: this.correlationId,
    requestId: this.requestId,
    metadata: this.metadata,
    occurredAt: this.occurredAt,
    createdAt: this.createdAt,
    updatedAt: this.updatedAt,
  };
};

const AuditLog = mongoose.models.AuditLog || mongoose.model('AuditLog', auditLogSchema);

module.exports = {
  AuditLog,
  auditLogSchema,
  AUDIT_CATEGORIES,
  AUDIT_OUTCOMES,
  AUDIT_SEVERITIES,
};
