'use client';

import { Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, Send } from 'lucide-react';
import { cn } from '../../lib/utils';

const navItems = [
  { label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { label: 'Payouts', href: '/payouts', icon: Send },
];

export function Sidebar() {
  const location = useLocation();
  const pathname = location.pathname;

  return (
    <aside className="w-16 md:w-64 bg-white border-r border-gray-200 h-screen sticky top-0 overflow-y-auto shrink-0">
      <div className="p-4">
        <div className="flex items-center justify-center md:justify-start md:gap-2 mb-8">
          <div className="w-10 h-10 rounded-lg bg-indigo-600 flex items-center justify-center shrink-0">
            <span className="text-white font-bold text-lg">P</span>
          </div>
          <span className="font-bold text-lg hidden md:block">Playto Console</span>
        </div>

        <nav className="space-y-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;

            return (
              <Link
                key={item.href}
                to={item.href}
                className={cn(
                  'flex items-center justify-center md:justify-start md:gap-3 px-2 md:px-4 py-3 rounded-lg font-medium transition-colors',
                  isActive
                    ? 'bg-indigo-50 text-indigo-700'
                    : 'text-gray-600 hover:bg-gray-50'
                )}
                title={item.label}
              >
                <Icon className="w-5 h-5" />
                <span className="hidden md:block">{item.label}</span>
              </Link>
            );
          })}
        </nav>
      </div>
    </aside>
  );
}
