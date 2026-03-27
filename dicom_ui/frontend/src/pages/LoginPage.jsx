import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiPost } from '../services/apiClient';
import { writeSession } from '../services/session';

const DEFAULT_FORM = {
  username: '',
  password: '',
};

function LoginPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState(DEFAULT_FORM);
  const [status, setStatus] = useState({
    isSubmitting: false,
    error: '',
  });

  function handleChange(event) {
    const { name, value } = event.target;
    setForm((current) => ({
      ...current,
      [name]: value,
    }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setStatus({ isSubmitting: true, error: '' });

    try {
      const payload = await apiPost('/auth/login', {
        username: form.username.trim(),
        password: form.password,
      });

      writeSession(payload);
      navigate('/dashboard', { replace: true });
    } catch (error) {
      setStatus({
        isSubmitting: false,
        error: error.message || 'Login failed',
      });
      return;
    }

    setStatus({ isSubmitting: false, error: '' });
  }

  return (
    <section className="login-layout">
      <article className="login-brief">
        <p className="eyebrow">Clinical Access</p>
        <h2>Secure sign-in for imaging operations.</h2>
        <p className="lead">
          Access transfer monitoring, study search, audit trails, and system health from one
          clinical control plane.
        </p>

        <div className="status-strip">
          <div>
            <span>Transport</span>
            <strong>TLS enforced</strong>
          </div>
          <div>
            <span>Access model</span>
            <strong>Role-based</strong>
          </div>
          <div>
            <span>Backend</span>
            <strong>Guardian linked</strong>
          </div>
        </div>
      </article>

      <article className="login-card">
        <header className="login-card__header">
          <p className="eyebrow">Authentication</p>
          <h3>Sign in to DICOM UI</h3>
          <p>Use your clinical or administrative account credentials.</p>
        </header>

        <form className="login-form" onSubmit={handleSubmit}>
          <label className="field">
            <span>Username</span>
            <input
              type="text"
              name="username"
              autoComplete="username"
              placeholder="superadmin"
              value={form.username}
              onChange={handleChange}
              disabled={status.isSubmitting}
              required
            />
          </label>

          <label className="field">
            <span>Password</span>
            <input
              type="password"
              name="password"
              autoComplete="current-password"
              placeholder="Enter your password"
              value={form.password}
              onChange={handleChange}
              disabled={status.isSubmitting}
              required
            />
          </label>

          {status.error ? <p className="form-error">{status.error}</p> : null}

          <button className="login-button" type="submit" disabled={status.isSubmitting}>
            {status.isSubmitting ? 'Signing in...' : 'Sign in'}
          </button>
        </form>

        <footer className="login-card__footer">
          <p>Only authenticated personnel may access protected imaging workflows.</p>
        </footer>
      </article>
    </section>
  );
}

export default LoginPage;
