import { useState } from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import { Shield, Menu, X, LogOut, ShieldCheck } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export function Navbar() {
  const [open, setOpen] = useState(false);
  const { user, isAuthenticated, isAdmin, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    setOpen(false);
    navigate('/');
  };

  return (
    <nav className="navbar" role="navigation" aria-label="Main">
      <div className="navbar-inner">
        {/* Brand */}
        <Link to="/" className="navbar-brand" aria-label="FinGuard AI Home">
          <Shield size={20} />
          FinGuard AI
        </Link>

        {/* Navigation Links */}
        <ul className={`navbar-links${open ? ' open' : ''}`}>
          <li>
            <NavLink to="/" end onClick={() => setOpen(false)}>Home</NavLink>
          </li>
          <li>
            <NavLink to="/models" onClick={() => setOpen(false)}>Models</NavLink>
          </li>
          <li>
            <NavLink to="/csv" onClick={() => setOpen(false)}>CSV Analysis</NavLink>
          </li>
          <li>
            <NavLink to="/transaction" onClick={() => setOpen(false)}>Individual Transaction</NavLink>
          </li>
          <li>
            <NavLink to="/about" onClick={() => setOpen(false)}>About</NavLink>
          </li>

          {/* Mobile-only auth area (inside dropdown) */}
          <li className="navbar-mobile-auth">
            {isAuthenticated && user ? (
              <>
                <Link to="/dashboard" className="navbar-user-chip" onClick={() => setOpen(false)}>
                  <span className="navbar-avatar">{user.full_name?.charAt(0) || 'U'}</span>
                  <span>{user.full_name}</span>
                  <span className="navbar-role-tag">{user.role}</span>
                </Link>
                {isAdmin && (
                  <NavLink to="/admin" className="btn-signin-link" onClick={() => setOpen(false)}>
                    <ShieldCheck size={14} /> Admin
                  </NavLink>
                )}
                <button className="btn-ghost" onClick={handleLogout}>
                  <LogOut size={14} /> Sign Out
                </button>
              </>
            ) : (
              <>
                <Link to="/signin" className="btn-signin-link" onClick={() => setOpen(false)}>
                  Sign In
                </Link>
                <Link to="/signup" className="btn-signup" onClick={() => setOpen(false)}>
                  Sign Up
                </Link>
              </>
            )}
          </li>
        </ul>

        {/* Desktop auth area */}
        <div className="navbar-spacer" />
        <div className="navbar-auth desktop-only">
          {isAuthenticated && user ? (
            <>
              <Link to="/dashboard" className="navbar-user-chip">
                <span className="navbar-avatar">{user.full_name?.charAt(0) || 'U'}</span>
                <span style={{ maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {user.full_name}
                </span>
                <span className="navbar-role-tag">{user.role}</span>
              </Link>
              {isAdmin && (
                <NavLink to="/admin" className="btn-signin-link">
                  <ShieldCheck size={14} /> Admin
                </NavLink>
              )}
              <button className="btn-ghost" onClick={handleLogout} title="Sign Out">
                <LogOut size={16} />
              </button>
            </>
          ) : (
            <>
              <Link to="/signin" className="btn-signin-link">Sign In</Link>
              <Link to="/signup" className="btn-signup">Sign Up</Link>
            </>
          )}
        </div>

        {/* Mobile toggle */}
        <button
          className="navbar-toggle"
          onClick={() => setOpen(!open)}
          aria-label="Toggle menu"
          aria-expanded={open}
        >
          {open ? <X size={22} /> : <Menu size={22} />}
        </button>
      </div>
    </nav>
  );
}
