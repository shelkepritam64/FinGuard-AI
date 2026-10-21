import { Link } from 'react-router-dom';

export function Footer() {
  return (
    <footer className="footer">
      <div className="footer-links">
        <Link to="/about">About</Link>
        <Link to="/privacy">Privacy Policy</Link>
        <Link to="/terms">Terms</Link>
      </div>
      <p>
        FinGuard AI — Educational fraud-risk screening research project.
        Not for production financial use.
      </p>
    </footer>
  );
}
