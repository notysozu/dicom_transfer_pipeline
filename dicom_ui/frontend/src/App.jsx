import { useEffect, useState } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import AppShell from './components/AppShell';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import { apiGet } from './services/apiClient';
import { clearSession, readSession, writeSession } from './services/session';

function AuthGate({ requireAuth, children }) {
  const [status, setStatus] = useState({
    isLoading: true,
    isAuthenticated: false,
  });

  useEffect(() => {
    let cancelled = false;

    async function verifySession() {
      const session = readSession();
      if (!session?.accessToken) {
        if (!cancelled) {
          setStatus({
            isLoading: false,
            isAuthenticated: false,
          });
        }
        return;
      }

      try {
        const payload = await apiGet('/auth/me', session.accessToken);
        writeSession({
          ...session,
          user: {
            ...session.user,
            ...(payload.user || {}),
          },
        });

        if (!cancelled) {
          setStatus({
            isLoading: false,
            isAuthenticated: true,
          });
        }
      } catch (_error) {
        clearSession();

        if (!cancelled) {
          setStatus({
            isLoading: false,
            isAuthenticated: false,
          });
        }
      }
    }

    verifySession();

    return () => {
      cancelled = true;
    };
  }, []);

  if (status.isLoading) {
    return (
      <section className="auth-gate">
        <div className="auth-gate__panel">
          <p className="eyebrow">Session Check</p>
          <h2>Verifying access</h2>
          <p>We are confirming your stored session with the backend.</p>
        </div>
      </section>
    );
  }

  if (requireAuth) {
    return status.isAuthenticated ? children : <Navigate to="/login" replace />;
  }

  return status.isAuthenticated ? <Navigate to="/dashboard" replace /> : children;
}

function App() {
  return (
    <AppShell>
      <Routes>
        <Route
          path="/login"
          element={
            <AuthGate requireAuth={false}>
              <LoginPage />
            </AuthGate>
          }
        />
        <Route
          path="/dashboard"
          element={
            <AuthGate requireAuth>
              <DashboardPage />
            </AuthGate>
          }
        />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </AppShell>
  );
}

export default App;
