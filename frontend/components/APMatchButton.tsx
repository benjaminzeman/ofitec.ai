'use client';

import { useState } from 'react';
import APMatchDrawer from './APMatchDrawer';

interface APMatchButtonProps {
  invoice: {
    id: string | number; // factura id o numero de documento
    vendor_rut?: string;
    amount?: number;
    date?: string;
    project_id?: string | number;
  };
  className?: string;
  label?: string;
  userId?: string;
}

export default function APMatchButton({
  invoice,
  className = 'px-3 py-1.5 rounded-lg bg-amber-600 text-white',
  label = 'OC Match',
  userId,
}: APMatchButtonProps) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className={className}
        title="Asociar Orden(es) de Compra"
      >
        {label}
      </button>
      <APMatchDrawer open={open} onClose={() => setOpen(false)} invoice={invoice} userId={userId} />
    </>
  );
}
