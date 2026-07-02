import React from 'react';

const statusConfig = {
  completed:  { label: 'Completed',  cls: 'completed'  },
  failed:     { label: 'Failed',     cls: 'failed'     },
  pending:    { label: 'Pending',    cls: 'pending'    },
  processing: { label: 'Processing', cls: 'processing' },
};

export default function StatusBadge({ status }) {
  const cfg = statusConfig[status] || { label: status, cls: 'bypassed' };
  return (
    <span className={`badge ${cfg.cls}`}>
      <span className="badge-dot" />
      {cfg.label}
    </span>
  );
}
