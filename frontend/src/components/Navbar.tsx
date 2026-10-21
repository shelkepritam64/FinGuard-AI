import { useState } from 'react';
import { Link, NavLink } from 'react-router-dom';
import { Shield, Menu, X } from 'lucide-react';

const links = [
  { to: '/', label: 'Home' },
  { to: '/models', label: 'Models' },
  { to: '/csv', label: 'CSV Analysis' },
  { to: '/transaction', label: 'Individual Transaction' },
  { to: '/about', label: 'About' },
];

export function Navbar() {
  const [open, setOpen] = useState(false);

  return (
    <nav className="navbar" role="navigation" aria-label="Main">
      <div className="navbar-inner">
        <Link to="/" className="navbar-brand" aria-label="FinGuard AI Home">
          <Shield size={20} />
          FinGuard AI
        </Link>

        <ul className={`navbar-links${open ? ' open' : ''}`}>
          {links.map((l) => (
            <li key={l.to}>
              <NavLink
                to={l.to}
                end={l.to === '/'}
                onClick={() => setOpen(false)}
              >
                {l.label}
              </NavLink>
            </li>
          ))}
        </ul>

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
