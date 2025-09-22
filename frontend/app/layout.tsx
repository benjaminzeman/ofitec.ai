'use client';

import './globals.css';
import { Inter } from 'next/font/google';
import { useState } from 'react';
import { Sidebar } from '@/components/layout/Sidebar';
import Topbar from '@/components/layout/Topbar';
import { ToastProvider } from '@/components/ui/ToastContext';
import { ToastContainer } from '@/components/ui/ToastContainer';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
});

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen);
  };

  return (
    <html lang="es" className={inter.variable}>
      <body className="min-h-screen bg-slate-50 dark:bg-slate-900">
        <ToastProvider>
          <div className="flex h-screen">
            <Sidebar isOpen={sidebarOpen} />
            <div className="flex-1 flex flex-col overflow-hidden">
              <Topbar onSidebarToggle={toggleSidebar} sidebarOpen={sidebarOpen} />
              <main className="flex-1 overflow-x-hidden overflow-y-auto bg-slate-50 dark:bg-slate-900">
                {children}
              </main>
            </div>
          </div>
          <ToastContainer />
        </ToastProvider>
      </body>
    </html>
  );
}
