import { useMemo, useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { apiGet, apiPatch, apiPost } from '../services/apiClient';
import { clearSession, readSession } from '../services/session';
const DEFAULT_STUDY_FILTERS = {
  patientId: '',
  modality: '',
  limit: '10',
};
const DEFAULT_TRANSFER_FILTERS = {
  status: '',
  studyInstanceUid: '',
  limit: '10',
};
const DEFAULT_LOG_FILTERS = {
  status: '',
  studyInstanceUid: '',
  sopInstanceUid: '',
  limit: '10',
};
const DEFAULT_USER_FILTERS = {
  role: '',
  isActive: '',
  limit: '10',
};
const DEFAULT_CREATE_USER_FORM = {
  username: '',
  email: '',
  password: '',
  role: 'VIEWER',
  firstName: '',
  lastName: '',
  department: '',
  isActive: 'true',
  mustChangePassword: 'true',
};
const DEFAULT_UPDATE_USER_FORM = {
  userId: '',
  department: '',
  role: '',
  isActive: '',
  mustChangePassword: '',
  password: '',
};

function formatUnixTimestamp(value) {
  if (!value || Number.isNaN(Number(value))) {
    return 'Unavailable';
  }

  return new Date(Number(value) * 1000).toLocaleString();
}

function buildStudyQuery(filters) {
  const params = new URLSearchParams();

  if (filters.patientId.trim()) {
    params.set('patient_id', filters.patientId.trim());
  }
  if (filters.modality.trim()) {
    params.set('modality', filters.modality.trim().toUpperCase());
  }
  if (filters.limit.trim()) {
    params.set('limit', filters.limit.trim());
  }

  const query = params.toString();
  return query ? `/studies?${query}` : '/studies';
}

function buildTransferQuery(filters) {
  const params = new URLSearchParams();

  if (filters.status.trim()) {
    params.set('status', filters.status.trim().toUpperCase());
  }
  if (filters.studyInstanceUid.trim()) {
    params.set('study_instance_uid', filters.studyInstanceUid.trim());
  }
  if (filters.limit.trim()) {
    params.set('limit', filters.limit.trim());
  }

  const query = params.toString();
  return query ? `/transfers?${query}` : '/transfers';
}

function buildLogQuery(filters) {
  const params = new URLSearchParams();

  if (filters.status.trim()) {
    params.set('status', filters.status.trim().toUpperCase());
  }
  if (filters.studyInstanceUid.trim()) {
    params.set('study_instance_uid', filters.studyInstanceUid.trim());
  }
  if (filters.sopInstanceUid.trim()) {
    params.set('sop_instance_uid', filters.sopInstanceUid.trim());
  }
  if (filters.limit.trim()) {
    params.set('limit', filters.limit.trim());
  }

  const query = params.toString();
  return query ? `/logs?${query}` : '/logs';
}

function buildUserQuery(filters) {
  const params = new URLSearchParams();

  if (filters.role.trim()) {
    params.set('role', filters.role.trim().toUpperCase());
  }
  if (filters.isActive.trim()) {
    params.set('isActive', filters.isActive.trim());
  }
  if (filters.limit.trim()) {
    params.set('limit', filters.limit.trim());
  }

  const query = params.toString();
  return query ? `/users?${query}` : '/users';
}

function getUserRecordId(account) {
  return account?.id || account?._id || '';
}

function DashboardPage() {
  const navigate = useNavigate();
  const session = readSession();
  const [studyFilters, setStudyFilters] = useState(DEFAULT_STUDY_FILTERS);
  const [studyState, setStudyState] = useState({
    isLoading: false,
    error: '',
    items: [],
    count: 0,
    hasSearched: false,
  });
  const [transferFilters, setTransferFilters] = useState(DEFAULT_TRANSFER_FILTERS);
  const [transferState, setTransferState] = useState({
    isLoading: false,
    error: '',
    items: [],
    count: 0,
    hasSearched: false,
  });
  const [logFilters, setLogFilters] = useState(DEFAULT_LOG_FILTERS);
  const [logState, setLogState] = useState({
    isLoading: false,
    error: '',
    items: [],
    count: 0,
    hasSearched: false,
  });
  const [metricsState, setMetricsState] = useState({
    isLoading: false,
    error: '',
    metrics: null,
    hasLoaded: false,
  });
  const [userFilters, setUserFilters] = useState(DEFAULT_USER_FILTERS);
  const [userState, setUserState] = useState({
    isLoading: false,
    error: '',
    items: [],
    count: 0,
    hasLoaded: false,
  });
  const [createUserForm, setCreateUserForm] = useState(DEFAULT_CREATE_USER_FORM);
  const [createUserState, setCreateUserState] = useState({
    isSubmitting: false,
    error: '',
    success: '',
  });
  const [updateUserForm, setUpdateUserForm] = useState(DEFAULT_UPDATE_USER_FORM);
  const [updateUserState, setUpdateUserState] = useState({
    isSubmitting: false,
    error: '',
    success: '',
  });
  const [userActionState, setUserActionState] = useState({
    error: '',
    success: '',
  });
  const [logoutState, setLogoutState] = useState({
    isSubmitting: false,
    error: '',
  });

  if (!session?.user || !session?.accessToken) {
    return <Navigate to="/login" replace />;
  }

  const user = session.user;
  const permissions = Array.isArray(user.permissions) ? user.permissions : [];
  const canReadStudies = permissions.includes('studies:read');
  const canReadTransfers = permissions.includes('transfers:read');
  const canReadLogs = permissions.includes('logs:read');
  const canViewMetrics = canReadStudies || canReadTransfers || canReadLogs;
  const canManageUsers = permissions.includes('users:manage');
  const token = session.accessToken;
  const activeStudySummary = useMemo(() => {
    const parts = [];

    if (studyFilters.patientId.trim()) {
      parts.push(`Patient ${studyFilters.patientId.trim()}`);
    }
    if (studyFilters.modality.trim()) {
      parts.push(`Modality ${studyFilters.modality.trim().toUpperCase()}`);
    }

    return parts.length > 0 ? parts.join(' • ') : 'All available studies';
  }, [studyFilters]);
  const activeTransferSummary = useMemo(() => {
    const parts = [];

    if (transferFilters.status.trim()) {
      parts.push(`Status ${transferFilters.status.trim().toUpperCase()}`);
    }
    if (transferFilters.studyInstanceUid.trim()) {
      parts.push(`Study ${transferFilters.studyInstanceUid.trim()}`);
    }

    return parts.length > 0 ? parts.join(' • ') : 'All transfer records';
  }, [transferFilters]);
  const activeLogSummary = useMemo(() => {
    const parts = [];

    if (logFilters.status.trim()) {
      parts.push(`Status ${logFilters.status.trim().toUpperCase()}`);
    }
    if (logFilters.studyInstanceUid.trim()) {
      parts.push(`Study ${logFilters.studyInstanceUid.trim()}`);
    }
    if (logFilters.sopInstanceUid.trim()) {
      parts.push(`SOP ${logFilters.sopInstanceUid.trim()}`);
    }

    return parts.length > 0 ? parts.join(' • ') : 'All integrity events';
  }, [logFilters]);
  const activeUserSummary = useMemo(() => {
    const parts = [];

    if (userFilters.role.trim()) {
      parts.push(`Role ${userFilters.role.trim().toUpperCase()}`);
    }
    if (userFilters.isActive.trim()) {
      parts.push(userFilters.isActive === 'true' ? 'Active only' : 'Inactive only');
    }

    return parts.length > 0 ? parts.join(' • ') : 'All manageable users';
  }, [userFilters]);

  async function handleSignOut() {
    setLogoutState({
      isSubmitting: true,
      error: '',
    });

    try {
      await apiPost('/auth/logout', {}, token);
      clearSession();
      navigate('/login', { replace: true });
      return;
    } catch (error) {
      setLogoutState({
        isSubmitting: false,
        error: error.message || 'Logout failed.',
      });
    }
  }

  function handleStudyFilterChange(event) {
    const { name, value } = event.target;
    setStudyFilters((current) => ({
      ...current,
      [name]: value,
    }));
  }

  function handleTransferFilterChange(event) {
    const { name, value } = event.target;
    setTransferFilters((current) => ({
      ...current,
      [name]: value,
    }));
  }

  function handleLogFilterChange(event) {
    const { name, value } = event.target;
    setLogFilters((current) => ({
      ...current,
      [name]: value,
    }));
  }

  function handleUserFilterChange(event) {
    const { name, value } = event.target;
    setUserFilters((current) => ({
      ...current,
      [name]: value,
    }));
  }

  function handleCreateUserChange(event) {
    const { name, value } = event.target;
    setCreateUserForm((current) => ({
      ...current,
      [name]: value,
    }));
  }

  function handleUpdateUserChange(event) {
    const { name, value } = event.target;
    setUpdateUserForm((current) => ({
      ...current,
      [name]: value,
    }));
  }

  function handleSelectUserForUpdate(account) {
    const userId = getUserRecordId(account);

    setUpdateUserForm({
      ...DEFAULT_UPDATE_USER_FORM,
      userId,
      department: account?.department || '',
      role: account?.role || '',
      isActive:
        typeof account?.isActive === 'boolean' ? String(account.isActive) : '',
      mustChangePassword:
        typeof account?.mustChangePassword === 'boolean'
          ? String(account.mustChangePassword)
          : '',
    }));
    setUpdateUserState({
      isSubmitting: false,
      error: '',
      success: userId
        ? `Loaded ${account.username || 'selected user'} into the update form.`
        : 'This user record does not expose an identifier.',
    });
    setUserActionState({
      error: '',
      success: userId
        ? `Prepared ${account.username || 'selected user'} for editing.`
        : '',
    });
  }

  async function handleCopyUserId(account) {
    const userId = getUserRecordId(account);

    if (!userId) {
      setUserActionState({
        error: 'This user record does not expose an identifier to copy.',
        success: '',
      });
      return;
    }

    try {
      await navigator.clipboard.writeText(userId);
      setUserActionState({
        error: '',
        success: `Copied user ID for ${account.username || 'selected user'}.`,
      });
    } catch (_error) {
      setUserActionState({
        error: 'Clipboard copy failed in this browser context.',
        success: '',
      });
    }
  }

  async function handleStudySearch(event) {
    event.preventDefault();

    if (!canReadStudies) {
      setStudyState({
        isLoading: false,
        error: 'Your role does not include study search access.',
        items: [],
        count: 0,
        hasSearched: true,
      });
      return;
    }

    setStudyState((current) => ({
      ...current,
      isLoading: true,
      error: '',
    }));

    try {
      const payload = await apiGet(buildStudyQuery(studyFilters), token);

      setStudyState({
        isLoading: false,
        error: '',
        items: Array.isArray(payload.studies) ? payload.studies : [],
        count: typeof payload.count === 'number' ? payload.count : 0,
        hasSearched: true,
      });
    } catch (error) {
      setStudyState({
        isLoading: false,
        error: error.message || 'Study search failed.',
        items: [],
        count: 0,
        hasSearched: true,
      });
    }
  }

  async function handleTransferSearch(event) {
    event.preventDefault();

    if (!canReadTransfers) {
      setTransferState({
        isLoading: false,
        error: 'Your role does not include transfer monitoring access.',
        items: [],
        count: 0,
        hasSearched: true,
      });
      return;
    }

    setTransferState((current) => ({
      ...current,
      isLoading: true,
      error: '',
    }));

    try {
      const payload = await apiGet(buildTransferQuery(transferFilters), token);

      setTransferState({
        isLoading: false,
        error: '',
        items: Array.isArray(payload.transfers) ? payload.transfers : [],
        count: typeof payload.count === 'number' ? payload.count : 0,
        hasSearched: true,
      });
    } catch (error) {
      setTransferState({
        isLoading: false,
        error: error.message || 'Transfer search failed.',
        items: [],
        count: 0,
        hasSearched: true,
      });
    }
  }

  async function handleLogSearch(event) {
    event.preventDefault();

    if (!canReadLogs) {
      setLogState({
        isLoading: false,
        error: 'Your role does not include integrity log access.',
        items: [],
        count: 0,
        hasSearched: true,
      });
      return;
    }

    setLogState((current) => ({
      ...current,
      isLoading: true,
      error: '',
    }));

    try {
      const payload = await apiGet(buildLogQuery(logFilters), token);

      setLogState({
        isLoading: false,
        error: '',
        items: Array.isArray(payload.logs) ? payload.logs : [],
        count: typeof payload.count === 'number' ? payload.count : 0,
        hasSearched: true,
      });
    } catch (error) {
      setLogState({
        isLoading: false,
        error: error.message || 'Log retrieval failed.',
        items: [],
        count: 0,
        hasSearched: true,
      });
    }
  }

  async function handleMetricsLoad() {
    if (!canViewMetrics) {
      setMetricsState({
        isLoading: false,
        error: 'Your role does not include dashboard metrics access.',
        metrics: null,
        hasLoaded: true,
      });
      return;
    }

    setMetricsState((current) => ({
      ...current,
      isLoading: true,
      error: '',
    }));

    try {
      const payload = await apiGet('/metrics', token);
      setMetricsState({
        isLoading: false,
        error: '',
        metrics: payload.metrics || null,
        hasLoaded: true,
      });
    } catch (error) {
      setMetricsState({
        isLoading: false,
        error: error.message || 'Metrics retrieval failed.',
        metrics: null,
        hasLoaded: true,
      });
    }
  }

  async function handleUserLoad(event) {
    event?.preventDefault();

    if (!canManageUsers) {
      setUserState({
        isLoading: false,
        error: 'Your role does not include user administration access.',
        items: [],
        count: 0,
        hasLoaded: true,
      });
      return;
    }

    setUserState((current) => ({
      ...current,
      isLoading: true,
      error: '',
    }));

    try {
      const payload = await apiGet(buildUserQuery(userFilters), token);
      setUserState({
        isLoading: false,
        error: '',
        items: Array.isArray(payload.users) ? payload.users : [],
        count: typeof payload.count === 'number' ? payload.count : 0,
        hasLoaded: true,
      });
    } catch (error) {
      setUserState({
        isLoading: false,
        error: error.message || 'User listing failed.',
        items: [],
        count: 0,
        hasLoaded: true,
      });
    }
  }

  async function handleCreateUser(event) {
    event.preventDefault();

    if (!canManageUsers) {
      setCreateUserState({
        isSubmitting: false,
        error: 'Your role does not include user administration access.',
        success: '',
      });
      return;
    }

    setCreateUserState({
      isSubmitting: true,
      error: '',
      success: '',
    });

    try {
      const payload = {
        username: createUserForm.username.trim(),
        email: createUserForm.email.trim(),
        password: createUserForm.password,
        role: createUserForm.role,
        firstName: createUserForm.firstName.trim(),
        lastName: createUserForm.lastName.trim(),
        department: createUserForm.department.trim(),
        isActive: createUserForm.isActive === 'true',
        mustChangePassword: createUserForm.mustChangePassword === 'true',
      };

      await apiPost('/users', payload, token);

      setCreateUserState({
        isSubmitting: false,
        error: '',
        success: `User ${payload.username} created successfully.`,
      });
      setCreateUserForm(DEFAULT_CREATE_USER_FORM);

      if (userState.hasLoaded) {
        await handleUserLoad();
      }
    } catch (error) {
      setCreateUserState({
        isSubmitting: false,
        error: error.message || 'User creation failed.',
        success: '',
      });
    }
  }

  async function handleUpdateUser(event) {
    event.preventDefault();

    if (!canManageUsers) {
      setUpdateUserState({
        isSubmitting: false,
        error: 'Your role does not include user administration access.',
        success: '',
      });
      return;
    }

    setUpdateUserState({
      isSubmitting: true,
      error: '',
      success: '',
    });

    try {
      const payload = {};

      if (updateUserForm.department.trim()) {
        payload.department = updateUserForm.department.trim();
      }
      if (updateUserForm.role.trim()) {
        payload.role = updateUserForm.role.trim();
      }
      if (updateUserForm.isActive.trim()) {
        payload.isActive = updateUserForm.isActive === 'true';
      }
      if (updateUserForm.mustChangePassword.trim()) {
        payload.mustChangePassword = updateUserForm.mustChangePassword === 'true';
      }
      if (updateUserForm.password) {
        payload.password = updateUserForm.password;
      }

      await apiPatch(`/users/${updateUserForm.userId.trim()}`, payload, token);

      setUpdateUserState({
        isSubmitting: false,
        error: '',
        success: `User ${updateUserForm.userId.trim()} updated successfully.`,
      });
      setUpdateUserForm(DEFAULT_UPDATE_USER_FORM);

      if (userState.hasLoaded) {
        await handleUserLoad();
      }
    } catch (error) {
      setUpdateUserState({
        isSubmitting: false,
        error: error.message || 'User update failed.',
        success: '',
      });
    }
  }

  return (
    <section className="dashboard-layout">
      <article className="dashboard-hero">
        <div>
          <p className="eyebrow">Operations Dashboard</p>
          <h2>Welcome back, {user.firstName || user.username}.</h2>
          <p className="dashboard-lead">
            Your session is active and ready for study search, transfer monitoring, logs, and
            user administration workflows.
          </p>
        </div>

        <div className="dashboard-hero__actions">
          <span className="session-pill">Role: {user.role}</span>
          <button
            className="ghost-button"
            type="button"
            onClick={handleSignOut}
            disabled={logoutState.isSubmitting}
          >
            {logoutState.isSubmitting ? 'Signing out...' : 'Sign out'}
          </button>
        </div>
      </article>

      {logoutState.error ? <p className="form-error">{logoutState.error}</p> : null}

      <section className="dashboard-grid">
        <article className="dashboard-panel">
          <p className="eyebrow">Account</p>
          <h3>Authenticated user</h3>
          <dl className="details-list">
            <div>
              <dt>Username</dt>
              <dd>{user.username}</dd>
            </div>
            <div>
              <dt>Email</dt>
              <dd>{user.email || 'Unavailable'}</dd>
            </div>
            <div>
              <dt>Department</dt>
              <dd>{user.department || 'Unavailable'}</dd>
            </div>
            <div>
              <dt>Must change password</dt>
              <dd>{user.mustChangePassword ? 'Yes' : 'No'}</dd>
            </div>
          </dl>
        </article>

        <article className="dashboard-panel">
          <p className="eyebrow">Session</p>
          <h3>Token window</h3>
          <dl className="details-list">
            <div>
              <dt>Issued at</dt>
              <dd>{formatUnixTimestamp(session.issuedAt)}</dd>
            </div>
            <div>
              <dt>Expires at</dt>
              <dd>{formatUnixTimestamp(session.expiresAt)}</dd>
            </div>
            <div>
              <dt>Token type</dt>
              <dd>{session.tokenType || 'Unavailable'}</dd>
            </div>
            <div>
              <dt>Guardian access</dt>
              <dd>Ready for later dashboard widgets</dd>
            </div>
          </dl>
        </article>

        <article className="dashboard-panel dashboard-panel--wide">
          <p className="eyebrow">Metrics</p>
          <div className="panel-header">
            <div>
              <h3>Operational summary</h3>
              <p className="panel-copy">
                Pull top-level Guardian counts for studies, transfers, and integrity events.
              </p>
            </div>
            <div className="toolbar-actions">
              <button
                className="login-button"
                type="button"
                onClick={handleMetricsLoad}
                disabled={metricsState.isLoading}
              >
                {metricsState.isLoading ? 'Loading...' : 'Load metrics'}
              </button>
            </div>
          </div>

          {metricsState.error ? <p className="form-error">{metricsState.error}</p> : null}

          {metricsState.metrics ? (
            <div className="metrics-layout">
              <div className="metric-card">
                <span>Studies total</span>
                <strong>{metricsState.metrics.studies_total ?? 0}</strong>
              </div>
              <div className="metric-card">
                <span>Transfers total</span>
                <strong>{metricsState.metrics.transfers_total ?? 0}</strong>
              </div>
              <div className="metric-card">
                <span>Integrity events</span>
                <strong>{metricsState.metrics.integrity_events_total ?? 0}</strong>
              </div>

              <div className="metric-breakdown">
                <h4>Transfers by status</h4>
                <div className="metric-list">
                  {Object.entries(metricsState.metrics.transfers_by_status || {}).map(
                    ([status, count]) => (
                      <div key={status}>
                        <span>{status}</span>
                        <strong>{count}</strong>
                      </div>
                    )
                  )}
                </div>
              </div>

              <div className="metric-breakdown">
                <h4>Integrity by status</h4>
                <div className="metric-list">
                  {Object.entries(metricsState.metrics.integrity_by_status || {}).map(
                    ([status, count]) => (
                      <div key={status}>
                        <span>{status}</span>
                        <strong>{count}</strong>
                      </div>
                    )
                  )}
                </div>
              </div>
            </div>
          ) : metricsState.hasLoaded ? (
            <p className="empty-state">No metrics payload was returned from Guardian.</p>
          ) : (
            <p className="empty-state">
              Load metrics to get a one-glance operational summary for the control plane.
            </p>
          )}
        </article>

        <article className="dashboard-panel dashboard-panel--wide">
          <p className="eyebrow">Studies</p>
          <div className="panel-header">
            <div>
              <h3>Study search</h3>
              <p className="panel-copy">
                Query the Guardian-backed study index with patient and modality filters.
              </p>
            </div>
            <span className="session-pill">Scope: {activeStudySummary}</span>
          </div>

          <form className="toolbar-form" onSubmit={handleStudySearch}>
            <label className="field">
              <span>Patient ID</span>
              <input
                type="text"
                name="patientId"
                placeholder="PID-50"
                value={studyFilters.patientId}
                onChange={handleStudyFilterChange}
                disabled={studyState.isLoading}
              />
            </label>

            <label className="field">
              <span>Modality</span>
              <input
                type="text"
                name="modality"
                placeholder="CT"
                value={studyFilters.modality}
                onChange={handleStudyFilterChange}
                disabled={studyState.isLoading}
              />
            </label>

            <label className="field">
              <span>Limit</span>
              <input
                type="number"
                min="1"
                max="1000"
                name="limit"
                value={studyFilters.limit}
                onChange={handleStudyFilterChange}
                disabled={studyState.isLoading}
              />
            </label>

            <div className="toolbar-actions">
              <button className="login-button" type="submit" disabled={studyState.isLoading}>
                {studyState.isLoading ? 'Searching...' : 'Search studies'}
              </button>
            </div>
          </form>

          {studyState.error ? <p className="form-error">{studyState.error}</p> : null}

          {studyState.hasSearched ? (
            studyState.items.length > 0 ? (
              <div className="data-table-wrap">
                <div className="table-meta">
                  <strong>{studyState.count}</strong>
                  <span>matching studies returned from Guardian</span>
                </div>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Study Instance UID</th>
                      <th>Patient ID</th>
                      <th>Modality</th>
                    </tr>
                  </thead>
                  <tbody>
                    {studyState.items.map((study, index) => (
                      <tr key={study.study_instance_uid || `study-${index}`}>
                        <td>{study.study_instance_uid || 'Unavailable'}</td>
                        <td>{study.patient_id || 'Unavailable'}</td>
                        <td>{study.modality || 'Unavailable'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="empty-state">No studies matched the current filters.</p>
            )
          ) : (
            <p className="empty-state">
              Run a search to load the first live study data into the dashboard.
            </p>
          )}
        </article>

        <article className="dashboard-panel dashboard-panel--wide">
          <p className="eyebrow">Transfers</p>
          <div className="panel-header">
            <div>
              <h3>Transfer monitoring</h3>
              <p className="panel-copy">
                Inspect queued, retrying, failed, and completed transfers from Guardian.
              </p>
            </div>
            <span className="session-pill">Scope: {activeTransferSummary}</span>
          </div>

          <form className="toolbar-form" onSubmit={handleTransferSearch}>
            <label className="field">
              <span>Status</span>
              <input
                type="text"
                name="status"
                placeholder="RETRYING"
                value={transferFilters.status}
                onChange={handleTransferFilterChange}
                disabled={transferState.isLoading}
              />
            </label>

            <label className="field">
              <span>Study Instance UID</span>
              <input
                type="text"
                name="studyInstanceUid"
                placeholder="1.2.840..."
                value={transferFilters.studyInstanceUid}
                onChange={handleTransferFilterChange}
                disabled={transferState.isLoading}
              />
            </label>

            <label className="field">
              <span>Limit</span>
              <input
                type="number"
                min="1"
                max="1000"
                name="limit"
                value={transferFilters.limit}
                onChange={handleTransferFilterChange}
                disabled={transferState.isLoading}
              />
            </label>

            <div className="toolbar-actions">
              <button className="login-button" type="submit" disabled={transferState.isLoading}>
                {transferState.isLoading ? 'Loading...' : 'Load transfers'}
              </button>
            </div>
          </form>

          {transferState.error ? <p className="form-error">{transferState.error}</p> : null}

          {transferState.hasSearched ? (
            transferState.items.length > 0 ? (
              <div className="data-table-wrap">
                <div className="table-meta">
                  <strong>{transferState.count}</strong>
                  <span>matching transfer records returned from Guardian</span>
                </div>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Transfer UID</th>
                      <th>Status</th>
                      <th>Study UID</th>
                      <th>Source AE</th>
                      <th>Destination AE</th>
                      <th>Retries</th>
                    </tr>
                  </thead>
                  <tbody>
                    {transferState.items.map((transfer, index) => (
                      <tr key={transfer.transfer_uid || `transfer-${index}`}>
                        <td>{transfer.transfer_uid || 'Unavailable'}</td>
                        <td>{transfer.status || 'Unavailable'}</td>
                        <td>{transfer.study_instance_uid || 'Unavailable'}</td>
                        <td>{transfer.source_ae_title || 'Unavailable'}</td>
                        <td>{transfer.destination_ae_title || 'Unavailable'}</td>
                        <td>{transfer.retry_count ?? 'Unavailable'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="empty-state">No transfers matched the current filters.</p>
            )
          ) : (
            <p className="empty-state">
              Run a transfer query to load live queue and delivery status data.
            </p>
          )}
        </article>

        <article className="dashboard-panel dashboard-panel--wide">
          <p className="eyebrow">Logs</p>
          <div className="panel-header">
            <div>
              <h3>Integrity log retrieval</h3>
              <p className="panel-copy">
                Review checksum, corruption, and integrity events recorded by Guardian.
              </p>
            </div>
            <span className="session-pill">Scope: {activeLogSummary}</span>
          </div>

          <form className="toolbar-form toolbar-form--logs" onSubmit={handleLogSearch}>
            <label className="field">
              <span>Status</span>
              <input
                type="text"
                name="status"
                placeholder="CORRUPTED"
                value={logFilters.status}
                onChange={handleLogFilterChange}
                disabled={logState.isLoading}
              />
            </label>

            <label className="field">
              <span>Study Instance UID</span>
              <input
                type="text"
                name="studyInstanceUid"
                placeholder="1.2.840..."
                value={logFilters.studyInstanceUid}
                onChange={handleLogFilterChange}
                disabled={logState.isLoading}
              />
            </label>

            <label className="field">
              <span>SOP Instance UID</span>
              <input
                type="text"
                name="sopInstanceUid"
                placeholder="1.2.840..."
                value={logFilters.sopInstanceUid}
                onChange={handleLogFilterChange}
                disabled={logState.isLoading}
              />
            </label>

            <label className="field">
              <span>Limit</span>
              <input
                type="number"
                min="1"
                max="1000"
                name="limit"
                value={logFilters.limit}
                onChange={handleLogFilterChange}
                disabled={logState.isLoading}
              />
            </label>

            <div className="toolbar-actions">
              <button className="login-button" type="submit" disabled={logState.isLoading}>
                {logState.isLoading ? 'Loading...' : 'Load logs'}
              </button>
            </div>
          </form>

          {logState.error ? <p className="form-error">{logState.error}</p> : null}

          {logState.hasSearched ? (
            logState.items.length > 0 ? (
              <div className="data-table-wrap">
                <div className="table-meta">
                  <strong>{logState.count}</strong>
                  <span>matching integrity events returned from Guardian</span>
                </div>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Event Type</th>
                      <th>Status</th>
                      <th>Study UID</th>
                      <th>SOP UID</th>
                      <th>Reason</th>
                    </tr>
                  </thead>
                  <tbody>
                    {logState.items.map((logItem, index) => (
                      <tr key={logItem.id || `${logItem.sop_instance_uid || 'log'}-${index}`}>
                        <td>{logItem.event_type || 'Unavailable'}</td>
                        <td>{logItem.status || 'Unavailable'}</td>
                        <td>{logItem.study_instance_uid || 'Unavailable'}</td>
                        <td>{logItem.sop_instance_uid || 'Unavailable'}</td>
                        <td>{logItem.reason || 'Unavailable'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="empty-state">No integrity events matched the current filters.</p>
            )
          ) : (
            <p className="empty-state">
              Run a log query to inspect audit and integrity events from Guardian.
            </p>
          )}
        </article>

        <article className="dashboard-panel dashboard-panel--wide">
          <p className="eyebrow">Users</p>
          <div className="panel-header">
            <div>
              <h3>User management list</h3>
              <p className="panel-copy">
                View manageable user accounts exposed by the UI backend administration API.
              </p>
            </div>
            <span className="session-pill">Scope: {activeUserSummary}</span>
          </div>

          <form className="create-user-form" onSubmit={handleCreateUser}>
            <label className="field">
              <span>Username</span>
              <input
                type="text"
                name="username"
                value={createUserForm.username}
                onChange={handleCreateUserChange}
                disabled={createUserState.isSubmitting}
                required
              />
            </label>

            <label className="field">
              <span>Email</span>
              <input
                type="email"
                name="email"
                value={createUserForm.email}
                onChange={handleCreateUserChange}
                disabled={createUserState.isSubmitting}
                required
              />
            </label>

            <label className="field">
              <span>Password</span>
              <input
                type="password"
                name="password"
                value={createUserForm.password}
                onChange={handleCreateUserChange}
                disabled={createUserState.isSubmitting}
                required
              />
            </label>

            <label className="field">
              <span>Role</span>
              <select
                name="role"
                value={createUserForm.role}
                onChange={handleCreateUserChange}
                disabled={createUserState.isSubmitting}
              >
                <option value="SUPER_ADMIN">SUPER_ADMIN</option>
                <option value="ADMIN">ADMIN</option>
                <option value="RADIOLOGIST">RADIOLOGIST</option>
                <option value="TECHNICIAN">TECHNICIAN</option>
                <option value="VIEWER">VIEWER</option>
              </select>
            </label>

            <label className="field">
              <span>First name</span>
              <input
                type="text"
                name="firstName"
                value={createUserForm.firstName}
                onChange={handleCreateUserChange}
                disabled={createUserState.isSubmitting}
              />
            </label>

            <label className="field">
              <span>Last name</span>
              <input
                type="text"
                name="lastName"
                value={createUserForm.lastName}
                onChange={handleCreateUserChange}
                disabled={createUserState.isSubmitting}
              />
            </label>

            <label className="field">
              <span>Department</span>
              <input
                type="text"
                name="department"
                value={createUserForm.department}
                onChange={handleCreateUserChange}
                disabled={createUserState.isSubmitting}
              />
            </label>

            <label className="field">
              <span>Active state</span>
              <select
                name="isActive"
                value={createUserForm.isActive}
                onChange={handleCreateUserChange}
                disabled={createUserState.isSubmitting}
              >
                <option value="true">Active</option>
                <option value="false">Inactive</option>
              </select>
            </label>

            <label className="field">
              <span>Force password change</span>
              <select
                name="mustChangePassword"
                value={createUserForm.mustChangePassword}
                onChange={handleCreateUserChange}
                disabled={createUserState.isSubmitting}
              >
                <option value="true">Yes</option>
                <option value="false">No</option>
              </select>
            </label>

            <div className="toolbar-actions">
              <button
                className="login-button"
                type="submit"
                disabled={createUserState.isSubmitting}
              >
                {createUserState.isSubmitting ? 'Creating...' : 'Create user'}
              </button>
            </div>
          </form>

          {createUserState.error ? <p className="form-error">{createUserState.error}</p> : null}
          {createUserState.success ? (
            <p className="form-success">{createUserState.success}</p>
          ) : null}

          <form className="create-user-form" onSubmit={handleUpdateUser}>
            <label className="field">
              <span>User ID</span>
              <input
                type="text"
                name="userId"
                value={updateUserForm.userId}
                onChange={handleUpdateUserChange}
                disabled={updateUserState.isSubmitting}
                required
              />
            </label>

            <label className="field">
              <span>Department</span>
              <input
                type="text"
                name="department"
                value={updateUserForm.department}
                onChange={handleUpdateUserChange}
                disabled={updateUserState.isSubmitting}
              />
            </label>

            <label className="field">
              <span>Role</span>
              <select
                name="role"
                value={updateUserForm.role}
                onChange={handleUpdateUserChange}
                disabled={updateUserState.isSubmitting}
              >
                <option value="">Keep current</option>
                <option value="SUPER_ADMIN">SUPER_ADMIN</option>
                <option value="ADMIN">ADMIN</option>
                <option value="RADIOLOGIST">RADIOLOGIST</option>
                <option value="TECHNICIAN">TECHNICIAN</option>
                <option value="VIEWER">VIEWER</option>
              </select>
            </label>

            <label className="field">
              <span>Active state</span>
              <select
                name="isActive"
                value={updateUserForm.isActive}
                onChange={handleUpdateUserChange}
                disabled={updateUserState.isSubmitting}
              >
                <option value="">Keep current</option>
                <option value="true">Active</option>
                <option value="false">Inactive</option>
              </select>
            </label>

            <label className="field">
              <span>Force password change</span>
              <select
                name="mustChangePassword"
                value={updateUserForm.mustChangePassword}
                onChange={handleUpdateUserChange}
                disabled={updateUserState.isSubmitting}
              >
                <option value="">Keep current</option>
                <option value="true">Yes</option>
                <option value="false">No</option>
              </select>
            </label>

            <label className="field">
              <span>New password</span>
              <input
                type="password"
                name="password"
                value={updateUserForm.password}
                onChange={handleUpdateUserChange}
                disabled={updateUserState.isSubmitting}
              />
            </label>

            <div className="toolbar-actions">
              <button
                className="login-button"
                type="submit"
                disabled={updateUserState.isSubmitting}
              >
                {updateUserState.isSubmitting ? 'Updating...' : 'Update user'}
              </button>
            </div>
          </form>

          {updateUserState.error ? <p className="form-error">{updateUserState.error}</p> : null}
          {updateUserState.success ? (
            <p className="form-success">{updateUserState.success}</p>
          ) : null}
          {userActionState.error ? <p className="form-error">{userActionState.error}</p> : null}
          {userActionState.success ? (
            <p className="form-success">{userActionState.success}</p>
          ) : null}

          <form className="toolbar-form" onSubmit={handleUserLoad}>
            <label className="field">
              <span>Role</span>
              <select
                name="role"
                value={userFilters.role}
                onChange={handleUserFilterChange}
                disabled={userState.isLoading}
              >
                <option value="">All roles</option>
                <option value="SUPER_ADMIN">SUPER_ADMIN</option>
                <option value="ADMIN">ADMIN</option>
                <option value="RADIOLOGIST">RADIOLOGIST</option>
                <option value="TECHNICIAN">TECHNICIAN</option>
                <option value="VIEWER">VIEWER</option>
              </select>
            </label>

            <label className="field">
              <span>Active state</span>
              <select
                name="isActive"
                value={userFilters.isActive}
                onChange={handleUserFilterChange}
                disabled={userState.isLoading}
              >
                <option value="">Any</option>
                <option value="true">Active</option>
                <option value="false">Inactive</option>
              </select>
            </label>

            <label className="field">
              <span>Limit</span>
              <input
                type="number"
                min="1"
                max="1000"
                name="limit"
                value={userFilters.limit}
                onChange={handleUserFilterChange}
                disabled={userState.isLoading}
              />
            </label>

            <div className="toolbar-actions">
              <button className="login-button" type="submit" disabled={userState.isLoading}>
                {userState.isLoading ? 'Loading...' : 'Load users'}
              </button>
            </div>
          </form>

          {userState.error ? <p className="form-error">{userState.error}</p> : null}

          {userState.items.length > 0 ? (
            <div className="data-table-wrap">
              <div className="table-meta">
                <strong>{userState.count}</strong>
                <span>manageable user accounts returned by the backend</span>
              </div>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>User ID</th>
                    <th>Username</th>
                    <th>Email</th>
                    <th>Role</th>
                    <th>Department</th>
                    <th>Active</th>
                    <th>Must change password</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {userState.items.map((account, index) => (
                    <tr key={getUserRecordId(account) || account.username || `user-${index}`}>
                      <td>{getUserRecordId(account) || 'Unavailable'}</td>
                      <td>{account.username || 'Unavailable'}</td>
                      <td>{account.email || 'Unavailable'}</td>
                      <td>{account.role || 'Unavailable'}</td>
                      <td>{account.department || 'Unavailable'}</td>
                      <td>{account.isActive ? 'Yes' : 'No'}</td>
                      <td>{account.mustChangePassword ? 'Yes' : 'No'}</td>
                      <td className="table-actions-cell">
                        <button
                          className="table-action-button"
                          type="button"
                          onClick={() => handleSelectUserForUpdate(account)}
                          disabled={!getUserRecordId(account)}
                        >
                          Edit
                        </button>
                        <button
                          className="table-action-button table-action-button--secondary"
                          type="button"
                          onClick={() => handleCopyUserId(account)}
                          disabled={!getUserRecordId(account)}
                        >
                          Copy ID
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : userState.hasLoaded ? (
            <p className="empty-state">No users matched the current filters.</p>
          ) : (
            <p className="empty-state">
              Load users to inspect the current administrable accounts in the platform.
            </p>
          )}
        </article>

        <article className="dashboard-panel dashboard-panel--wide">
          <p className="eyebrow">Permissions</p>
          <h3>Role-derived access</h3>
          <div className="permission-list">
            {permissions.length > 0 ? (
              permissions.map((permission) => (
                <span className="permission-chip" key={permission}>
                  {permission}
                </span>
              ))
            ) : (
              <p className="empty-state">No permissions were attached to this session.</p>
            )}
          </div>
        </article>

        <article className="dashboard-panel dashboard-panel--wide">
          <p className="eyebrow">Roadmap</p>
          <h3>Widgets arriving next</h3>
          <div className="roadmap-strip">
            <div>
              <strong>Studies</strong>
              <p>Search and browse study metadata from Guardian.</p>
            </div>
            <div>
              <strong>Transfers</strong>
              <p>Track queue, retry, send, and failure status in one place.</p>
            </div>
            <div>
              <strong>Logs</strong>
              <p>Inspect integrity events and operational audit history.</p>
            </div>
            <div>
              <strong>Metrics</strong>
              <p>Summarize current system health for the control plane.</p>
            </div>
          </div>
        </article>
      </section>
    </section>
  );
}

export default DashboardPage;
