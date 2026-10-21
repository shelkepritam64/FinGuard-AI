import { Lock, EyeOff, Server } from 'lucide-react';

export function PrivacyPolicyPage() {
  return (
    <div className="page">
      <header className="page-header">
        <h1>Privacy Policy</h1>
        <p>
          FinGuard AI is an academic demonstration system. This document outlines our strict
          ephemeral data handling practices and privacy principles.
        </p>
      </header>

      {/* Overview */}
      <section className="mb-2">
        <p className="section-label">Data Collection Overview</p>
        <div className="card">
          <div className="card-body">
            <p className="card-text mb-1">
              FinGuard AI does not collect, store, share, or monetize any personally identifiable
              information (PII), banking credentials, account numbers, or real transaction histories.
            </p>
            <p className="card-text">
              The application processes all uploaded CSV files and transaction forms ephemerally
              in volatile system memory solely for the purpose of computing inference scores.
            </p>
          </div>
        </div>
      </section>

      {/* Key Guarantees */}
      <section className="mb-2">
        <p className="section-label">Core Privacy Principles</p>
        <div className="grid-3">
          <div className="card">
            <div className="card-body">
              <div className="flex items-center gap-1 mb-1">
                <Lock size={18} color="var(--blue-600)" />
                <h3 className="card-title" style={{ marginBottom: 0 }}>
                  Ephemeral In-Memory Processing
                </h3>
              </div>
              <p className="card-text">
                Uploaded CSV files are read into temporary RAM buffers, normalized through the
                preprocessing pipeline, scored, and discarded immediately after returning the
                response.
              </p>
            </div>
          </div>

          <div className="card">
            <div className="card-body">
              <div className="flex items-center gap-1 mb-1">
                <EyeOff size={18} color="var(--blue-600)" />
                <h3 className="card-title" style={{ marginBottom: 0 }}>
                  Zero Persistent Storage
                </h3>
              </div>
              <p className="card-text">
                No external relational database, NoSQL cluster, or third-party cloud data warehouse
                stores transactions screened by this system.
              </p>
            </div>
          </div>

          <div className="card">
            <div className="card-body">
              <div className="flex items-center gap-1 mb-1">
                <Server size={18} color="var(--blue-600)" />
                <h3 className="card-title" style={{ marginBottom: 0 }}>
                  No Third-Party Analytics
                </h3>
              </div>
              <p className="card-text">
                We do not integrate advertising trackers, behavioral analytics SDKs, or commercial
                telemetry beacons on this analytics interface.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* User Guidelines */}
      <section className="mb-2">
        <p className="section-label">Responsible Usage Guidelines</p>
        <div className="card">
          <div className="card-body">
            <ul
              style={{
                paddingLeft: '1.25rem',
                color: 'var(--fg-700)',
                fontSize: '0.867rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.5rem',
              }}
            >
              <li>
                <strong>Do Not Upload Live Production Financial Records:</strong> Users must refrain
                from uploading confidential client bank statements, real credit card numbers (PANs),
                or personally identifiable customer information.
              </li>
              <li>
                <strong>Anonymized Benchmark Data:</strong> Only test datasets, synthetic simulation
                data (such as PaySim), or de-identified research benchmarks should be evaluated with
                this tool.
              </li>
              <li>
                <strong>Local Hosting:</strong> Organizations or academic institutions evaluating this
                system should host both backend and frontend locally or within secured, private
                perimeter networks.
              </li>
            </ul>
          </div>
        </div>
      </section>

      {/* Contact */}
      <section>
        <p className="section-label">Academic Contact</p>
        <div className="card">
          <div className="card-body">
            <p className="card-text">
              For academic inquiries or research methodology questions regarding FinGuard AI, please
              refer to the project repository documentation.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
