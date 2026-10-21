import React from 'react';

export const Header: React.FC = () => {
  return (
    <header className="finguard-header">
      <div className="header-container">
        <div className="brand">
          <span className="brand-badge">Educational Project</span>
          <h1>FinGuard AI</h1>
        </div>
        <p className="tagline">Transaction Fraud-Risk Screening System</p>
      </div>
    </header>
  );
};
