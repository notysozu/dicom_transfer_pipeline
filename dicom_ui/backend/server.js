'use strict';

/**
 * dicom_ui backend HTTPS server bootstrap (Step 25).
 */

const https = require('node:https');
const express = require('express');

const { buildConfigFromEnv } = require('./config');
const { buildHttpsServerTlsOptions, tlsDiagnostics } = require('./config/tls');
const {
  connectToDatabase,
  disconnectFromDatabase,
  checkDatabaseConnection,
  getConnectionState,
} = require('./config/db');
const registerAuthRoutes = require('./routes/auth.routes');
const registerLogRoutes = require('./routes/log.routes');
const registerStudyRoutes = require('./routes/study.routes');
const registerTransferRoutes = require('./routes/transfer.routes');
const registerUserRoutes = require('./routes/user.routes');

function createApp(config) {
  const app = express();

  app.disable('x-powered-by');
  app.use(express.json({ limit: '1mb' }));

  app.get('/api/health', async (_req, res) => {
    const dbHealthy = await checkDatabaseConnection();
    const tlsInfo = tlsDiagnostics(config.tls);

    res.status(dbHealthy ? 200 : 503).json({
      service: 'dicom_ui_backend',
      status: dbHealthy ? 'ok' : 'degraded',
      environment: config.app.environment,
      database: {
        healthy: dbHealthy,
        connectionState: getConnectionState(),
      },
      tls: {
        certPath: tlsInfo.certPath,
        caPath: tlsInfo.caPath,
        rejectUnauthorized: tlsInfo.rejectUnauthorized,
      },
      timestamp: new Date().toISOString(),
    });
  });

  app.use('/api/auth', registerAuthRoutes());
  app.use('/api/logs', registerLogRoutes());
  app.use('/api/studies', registerStudyRoutes());
  app.use('/api/transfers', registerTransferRoutes());
  app.use('/api/users', registerUserRoutes());

  app.use((_req, res) => {
    return res.status(404).json({
      error: 'not_found',
      message: 'Route not found',
    });
  });

  return app;
}

function createHttpsServer(config) {
  const tlsOptions = buildHttpsServerTlsOptions(config.tls);
  const app = createApp(config);
  const server = https.createServer(tlsOptions, app);
  return { app, server };
}

function installShutdownHandlers(server) {
  const shutdown = async (signal) => {
    // eslint-disable-next-line no-console
    console.info(`[server] received ${signal}, shutting down`);
    server.close(async () => {
      await disconnectFromDatabase();
      process.exit(0);
    });
  };

  process.on('SIGINT', () => shutdown('SIGINT'));
  process.on('SIGTERM', () => shutdown('SIGTERM'));
}

async function startServer(options = {}) {
  const config = buildConfigFromEnv();
  const { server } = createHttpsServer(config);
  const connectDbOnStartup =
    typeof options.connectDbOnStartup === 'boolean' ? options.connectDbOnStartup : true;

  if (connectDbOnStartup) {
    await connectToDatabase(config.db);
  }

  await new Promise((resolve) => {
    server.listen(config.app.server.port, config.app.server.host, resolve);
  });

  installShutdownHandlers(server);

  // eslint-disable-next-line no-console
  console.info(
    `[server] HTTPS listening on https://${config.app.server.host}:${config.app.server.port}`
  );

  return { server, config };
}

if (require.main === module) {
  startServer().catch(async (error) => {
    // eslint-disable-next-line no-console
    console.error(`[server] startup failed: ${error.message}`);
    await disconnectFromDatabase();
    process.exit(1);
  });
}

module.exports = {
  createApp,
  createHttpsServer,
  startServer,
};
