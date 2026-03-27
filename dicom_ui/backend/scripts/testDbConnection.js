'use strict';

const { buildConfigFromEnv } = require('../config');
const {
  connectToDatabase,
  disconnectFromDatabase,
  checkDatabaseConnection,
  getConnectionState,
} = require('../config/db');

async function runDatabaseConnectionTest() {
  const config = buildConfigFromEnv();

  try {
    await connectToDatabase(config.db);
    const healthy = await checkDatabaseConnection();

    if (!healthy) {
      throw new Error('MongoDB ping failed');
    }

    // eslint-disable-next-line no-console
    console.log(`[ui-db-test] uri=${config.db.uri}`);
    // eslint-disable-next-line no-console
    console.log(`[ui-db-test] state=${getConnectionState()}`);
    // eslint-disable-next-line no-console
    console.log('[ui-db-test] result=PASS');
    return true;
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error(`[ui-db-test] result=FAIL reason=${error.message}`);
    return false;
  } finally {
    await disconnectFromDatabase();
  }
}

if (require.main === module) {
  runDatabaseConnectionTest().then((ok) => {
    process.exit(ok ? 0 : 1);
  });
}

module.exports = {
  runDatabaseConnectionTest,
};
