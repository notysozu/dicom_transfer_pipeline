const SESSION_STORAGE_KEY = 'dicom_ui_auth_session';

function readSession() {
  try {
    const rawValue = sessionStorage.getItem(SESSION_STORAGE_KEY);
    if (!rawValue) {
      return null;
    }

    return JSON.parse(rawValue);
  } catch (_error) {
    return null;
  }
}

function writeSession(session) {
  sessionStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session));
}

function clearSession() {
  sessionStorage.removeItem(SESSION_STORAGE_KEY);
}

export {
  SESSION_STORAGE_KEY,
  readSession,
  writeSession,
  clearSession,
};
