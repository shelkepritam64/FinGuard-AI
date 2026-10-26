import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Shield, Lock, Mail, AlertCircle, ArrowRight, Loader2, Eye, EyeOff } from 'lucide-react';

export const SignInPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const { login, clearError } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const from = (location.state as any)?.from?.pathname || '/dashboard';

  const validateEmail = (e: string): boolean => {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e.trim());
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    clearError();

    if (!email.trim()) {
      setFormError('Please enter your email address.');
      return;
    }
    if (!validateEmail(email)) {
      setFormError('Please enter a valid email address.');
      return;
    }
    if (!password) {
      setFormError('Please enter your password.');
      return;
    }

    try {
      setSubmitting(true);
      const profile = await login(email.trim().toLowerCase(), password);
      if (from && from !== '/login' && from !== '/signin') {
        navigate(from, { replace: true });
      } else {
        navigate(profile.role === 'admin' ? '/admin' : '/dashboard', { replace: true });
      }
    } catch (err: any) {
      setFormError(err?.message || 'Authentication failed. Please check your credentials.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        {/* Header */}
        <div className="auth-header">
          <div className="auth-brand">
            <Shield size={24} />
          </div>
          <h1>Welcome back</h1>
          <p>Sign in to access your fraud screening dashboard</p>
        </div>

        {/* Error */}
        {formError && (
          <div className="auth-error">
            <AlertCircle size={18} />
            <span>{formError}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="auth-form" id="signin-form">
          {/* Email */}
          <div className="form-group">
            <label htmlFor="signin-email" className="form-label">Email Address</label>
            <div className="input-icon-wrap">
              <Mail size={16} className="input-icon-left" />
              <input
                id="signin-email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => { setEmail(e.target.value); setFormError(null); }}
                placeholder="you@domain.com"
                className="form-input"
              />
            </div>
          </div>

          {/* Password */}
          <div className="form-group">
            <label htmlFor="signin-password" className="form-label">Password</label>
            <div className="input-icon-wrap">
              <Lock size={16} className="input-icon-left" />
              <input
                id="signin-password"
                type={showPassword ? 'text' : 'password'}
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => { setPassword(e.target.value); setFormError(null); }}
                placeholder="Enter your password"
                className="form-input has-right-btn"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="input-icon-btn"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
                tabIndex={-1}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          {/* Submit */}
          <button
            type="submit"
            disabled={submitting}
            id="signin-submit"
            className="btn btn-primary w-full"
            style={{ justifyContent: 'center', height: 42 }}
          >
            {submitting ? (
              <>
                <Loader2 size={16} className="spinner-inline" />
                <span>Signing in…</span>
              </>
            ) : (
              <>
                <span>Sign In</span>
                <ArrowRight size={15} />
              </>
            )}
          </button>
        </form>

        {/* Sign Up link */}
        <div className="auth-footer">
          <p>
            Don't have an account?{' '}
            <Link to="/signup" state={location.state}>Create Account</Link>
          </p>
        </div>
      </div>
    </div>
  );
};
