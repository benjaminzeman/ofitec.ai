'use client';

import { useState } from 'react';
import ReconcileDrawer from './ReconcileDrawer';

type SourceType = 'bank' | 'purchase' | 'sales' | 'expense' | 'payroll' | 'tax';

export default function ConciliarButton({
  sourceType,
  getSource,
  className = 'px-3 py-1.5 rounded-lg bg-indigo-600 text-white',
}: {
  sourceType: SourceType;
  getSource: () => { id?: number; amount?: number; date?: string; ref?: string; currency?: string };
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  const [source, setSource] = useState<{
    id?: number;
    amount?: number;
    date?: string;
    ref?: string;
    currency?: string;
  }>({});

  const onClick = () => {
    setSource(getSource());
    setOpen(true);
  };

  return (
    <>
      <button onClick={onClick} className={className}>
        Conciliar
      </button>
      <ReconcileDrawer
        open={open}
        onClose={() => setOpen(false)}
        sourceType={sourceType}
        source={source}
      />
    </>
  );
}
