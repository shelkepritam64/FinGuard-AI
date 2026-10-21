import { AlertTriangle, Inbox } from 'lucide-react';

export function Loading({ message = 'Loading…' }: { message?: string }) {
  return (
    <div className="state-box">
      <div className="spinner" role="status" />
      <p>{message}</p>
    </div>
  );
}

export function ErrorBox({ message }: { message: string }) {
  return (
    <div className="alert alert-error" role="alert">
      <AlertTriangle size={18} />
      <span>{message}</span>
    </div>
  );
}

export function EmptyState({ message = 'No data available.' }: { message?: string }) {
  return (
    <div className="state-box">
      <Inbox size={32} />
      <p>{message}</p>
    </div>
  );
}
