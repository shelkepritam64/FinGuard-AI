import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Shield, Lock, Mail, User, AlertCircle, ArrowRight, Loader2, Eye, EyeOff, Check, X } from 'lucide-react';

export const SignUpPage: React.FC = () => {
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const { register, clearError } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const validateEmail = (e: string): boolean => {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e.trim());
  };

  // Password strength checks
  const hasMinLength = password.length >= 8;
  const hasUppercase = /[A-Z]/.test(password);
  const hasLowercase = /[a-z]/.test(password);
  const hasDigit = /[0-9]/.test(password);
  const isPasswordValid = hasMinLength && hasUppercase && hasLowercase && hasDigit;
  const passwordsMatch = password.length > 0 && password === confirmPassword;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    clearError();

    if (!fullName.trim()) {
      setFormError('Please enter your full name.');
      return;
    }

    if (!email.trim()) {
      setFormError('Please enter your email address.');
      return;
    }

    if (!validateEmail(email)) {
      setFormError('Please enter a valid email address.');
      return;
    }

    if (!isPasswordValid) {
      setFormError('Password does not meet the security requirements.');
      return;
    }

    if (!passwordsMatch) {
      setFormError('Passwords do not match.');
      return;
    }

    try {
      setSubmitting(true);
      await register(email.trim().toLowerCase(), password, fullName.trim());
      navigate('/dashboard', { replace: true });
    } catch (err: any) {
      setFormError(err?.message || 'Registration failed. Please try again.');
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
          <h1>Create FinGuard Account</h1>
          <p>Access AI fraud screening models and track batch analytics</p>
        </div>

        {/* Error Alert */}
        {formError && (
          <div className="auth-error">
            <AlertCircle size={18} />
            <span>{formError}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="auth-form" id="signup-form">
          {/* Full Name */}
          <div className="form-group">
            <label htmlFor="signup-name" className="form-label">Full Name</label>
            <div className="input-icon-wrap">
              <User size={16} className="input-icon-left" />
              <input
                id="signup-name"
                type="text"
                autoComplete="name"
                required
                value={fullName}
                onChange={(e) => { setFullName(e.target.value); setFormError(null); }}
                placeholder="Jane Doe"
                className="form-input"
              />
            </div>
          </div>

          {/* Email */}
          <div className="form-group">
            <label htmlFor="signup-email" className="form-label">Email Address</label>
            <div className="input-icon-wrap">
              <Mail size={16} className="input-icon-left" />
              <input
                id="signup-email"
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

          {/* Password with show/hide */}
          <div className="form-group">
            <label htmlFor="signup-password" className="form-label">Password</label>
            <div className="input-icon-wrap">
              <Lock size={16} className="input-icon-left" />
              <input
                id="signup-password"
                type={showPassword ? 'text' : 'password'}
                autoComplete="new-password"
                required
                value={password}
                onChange={(e) => { setPassword(e.target.value); setFormError(null); }}
                placeholder="Create a strong password"
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

          {/* Confirm Password */}
          <div className="form-group">
            <label htmlFor="signup-confirm-password" className="form-label">Confirm Password</label>
            <div className="input-icon-wrap">
              <Lock size={16} className="input-icon-left" />
              <input
                id="signup-confirm-password"
                type={showConfirmPassword ? 'text' : 'password'}
                autoComplete="new-password"
                required
                value={confirmPassword}
                onChange={(e) => { setConfirmPassword(e.target.value); setFormError(null); }}
                placeholder="Re-enter your password"
                className="form-input has-right-btn"
              />
              <button
                type="button"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                className="input-icon-btn"
                aria-label={showConfirmPassword ? 'Hide confirm password' : 'Show confirm password'}
                tabIndex={-1}
              >
                {showConfirmPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
            {confirmPassword && (
              <div className={`pw-match ${passwordsMatch ? 'ok' : 'fail'}`}>
                {passwordsMatch ? (
                  <>
                    <Check size={13} />
                    <span>Passwords match</span>
                  </>
                ) : (
                  <>
                    <X size={13} />
                    <span>Passwords do not match</span>
                  </>
                )}
              </div>
            )}
          </div>

          {/* Password Requirements Checklist */}
          <div className="pw-requirements">
            <div className="pw-requirements-title">Password Requirements</div>
            <div className="pw-check-grid">
              <div className={`pw-check ${hasMinLength ? 'pass' : ''}`}>
                {hasMinLength ? <Check size={12} /> : <span style={{ width: 10, height: 10, borderRadius: '50%', border: '1px solid var(--fg-300)', display: 'inline-block' }} />}
                <span>8+ characters</span>
              </div>
              <div className={`pw-check ${hasUppercase ? 'pass' : ''}`}>
                {hasUppercase ? <Check size={12} /> : <span style={{ width: 10, height: 10, borderRadius: '50%', border: '1px solid var(--fg-300)', display: 'inline-block' }} />}
                <span>Uppercase (A-Z)</span>
              </div>
              <div className={`pw-check ${hasLowercase ? 'pass' : ''}`}>
                {hasLowercase ? <Check size={12} /> : <span style={{ width: 10, height: 10, borderRadius: '50%', border: '1px solid var(--fg-300)', display: 'inline-block' }} />}
                <span>Lowercase (a-z)</span>
              </div>
              <div className={`pw-check ${hasDigit ? 'pass' : ''}`}>
                {hasDigit ? <Check size={12} /> : <span style={{ width: 10, height: 10, borderRadius: '50%', border: '1px solid var(--fg-300)', display: 'inline-block' }} />}
                <span>Number (0-9)</span>
              </div>
            </div>
          </div>

          {/* Submit */}
          <button
            type="submit"
            disabled={submitting}
            id="signup-submit"
            className="btn btn-primary w-full"
            style={{ justifyContent: 'center', height: 42, marginTop: '0.5rem' }}
          >
            {submitting ? (
              <>
                <Loader2 size={16} className="spinner-inline" />
                <span>Creating account…</span>
              </>
            ) : (
              <>
                <span>Create Account</span>
                <ArrowRight size={15} />
              </>
            )}
          </button>
        </form>

        {/* Sign In link */}
        <div className="auth-footer">
          <p>
            Already have an account?{' '}
            <Link to="/signin" state={location.state}>Sign In</Link>
          </p>
        </div>
      </div>
    </div>
  );
};
