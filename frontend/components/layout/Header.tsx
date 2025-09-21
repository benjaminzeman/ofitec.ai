'use client';

import { Bell, Search, User, Sun, Moon } from 'lucide-react';
import { useState } from 'react';

export function Header() {
  const [isDark, setIsDark] = useState(true);

  const toggleTheme = () => {
    setIsDark(!isDark);
    document.documentElement.classList.toggle('light');
  };

  return (
    <header className="h-16 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between px-6">
      {/* Search */}
      <div className="flex-1 max-w-md">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-500 dark:text-slate-400 h-4 w-4" />
          <input
            type="text"
            placeholder="Buscar en ofitec.ai..."
            className="w-full pl-10 pr-4 py-2 bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-900 dark:text-slate-100 placeholder-slate-500 dark:placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-lime-500 focus:border-transparent text-sm"
          />
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center space-x-4">
        {/* Theme Toggle */}
        <button
          onClick={toggleTheme}
          className="p-2 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
        >
          {isDark ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
        </button>

        {/* Notifications */}
        <button className="relative p-2 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">
          <Bell className="h-5 w-5" />
          <span className="absolute top-1 right-1 w-2 h-2 bg-lime-500 rounded-full"></span>
        </button>

        {/* User Menu */}
        <div className="relative">
          <button className="flex items-center space-x-2 p-2 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">
            <User className="h-5 w-5" />
            <span className="text-sm">Admin</span>
          </button>
        </div>
      </div>
    </header>
  );
}
