import { useState, useRef, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import './AuthPage.css';

export default function AuthPage() {
  const [isLogin, setIsLogin] = useState(true);
  const { login, register, authError } = useAuth();
  const [loading, setLoading] = useState(false);

  // Controlled state for live button-disabled logic
  const [fields, setFields] = useState({ name: '', email: '', password: '', confirmPassword: '' });

  // Refs to always read the actual DOM value at submit time (autofill-safe)
  const nameRef = useRef(null);
  const emailRef = useRef(null);
  const passwordRef = useRef(null);
  const confirmPasswordRef = useRef(null);

  // Sync autofill: browsers may fill inputs without firing onChange.
  // onInput fires on programmatic changes AND autofill in modern browsers.
  const handleInput = (e) => {
    setFields(prev => ({ ...prev, [e.target.name]: e.target.value }));
  };

  // Reset field state when toggling between login and register
  useEffect(() => {
    setFields({ name: '', email: '', password: '', confirmPassword: '' });
  }, [isLogin]);

  const canSubmit = () => {
    // Read DOM values directly — immune to autofill not triggering state
    const email = emailRef.current?.value || '';
    const password = passwordRef.current?.value || '';
    if (isLogin) return email.trim() !== '' && password.trim() !== '';
    const name = nameRef.current?.value || '';
    const confirmPassword = confirmPasswordRef.current?.value || '';
    return name.trim() !== '' && email.trim() !== '' && password.trim() !== '' && confirmPassword.trim() !== '';
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Always read from DOM refs at submit time — safe against autofill
    const email = emailRef.current?.value || '';
    const password = passwordRef.current?.value || '';

    if (!email || !password) return;

    setLoading(true);

    if (isLogin) {
      await login(email, password);
    } else {
      const name = nameRef.current?.value || '';
      const confirmPassword = confirmPasswordRef.current?.value || '';

      if (password !== confirmPassword) {
        alert('Passwords do not match');
        setLoading(false);
        return;
      }
      await register(name, email, password, confirmPassword);
    }
    setLoading(false);
  };

  const isButtonDisabled = loading;

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h2>{isLogin ? 'Login to DevAgent' : 'Create an Account'}</h2>

        {authError && <div className="auth-error">{authError}</div>}

        <form onSubmit={handleSubmit} noValidate>
          {!isLogin && (
            <div className="form-group">
              <label htmlFor="auth-name">Name</label>
              <input
                id="auth-name"
                ref={nameRef}
                type="text"
                name="name"
                value={fields.name}
                onChange={handleInput}
                onInput={handleInput}
                autoComplete="name"
                required
              />
            </div>
          )}

          <div className="form-group">
            <label htmlFor="auth-email">Email</label>
            <input
              id="auth-email"
              ref={emailRef}
              type="email"
              name="email"
              value={fields.email}
              onChange={handleInput}
              onInput={handleInput}
              autoComplete="email"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="auth-password">Password</label>
            <input
              id="auth-password"
              ref={passwordRef}
              type="password"
              name="password"
              value={fields.password}
              onChange={handleInput}
              onInput={handleInput}
              autoComplete={isLogin ? 'current-password' : 'new-password'}
              required
            />
          </div>

          {!isLogin && (
            <div className="form-group">
              <label htmlFor="auth-confirm-password">Confirm Password</label>
              <input
                id="auth-confirm-password"
                ref={confirmPasswordRef}
                type="password"
                name="confirmPassword"
                value={fields.confirmPassword}
                onChange={handleInput}
                onInput={handleInput}
                autoComplete="new-password"
                required
              />
            </div>
          )}

          <button
            type="submit"
            disabled={isButtonDisabled}
            className="auth-button"
          >
            {loading ? 'Processing...' : (isLogin ? 'Login' : 'Sign Up')}
          </button>
        </form>

        <p className="auth-toggle">
          {isLogin ? "Don't have an account? " : 'Already have an account? '}
          <button type="button" onClick={() => setIsLogin(!isLogin)} className="toggle-btn">
            {isLogin ? 'Sign up' : 'Login'}
          </button>
        </p>
      </div>
    </div>
  );
}

