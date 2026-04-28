'use client';

import { Sidebar } from './Sidebar';
import { Header } from './Header';

interface DashboardLayoutProps {
  children: React.ReactNode;
  merchantName?: string;
  isSyncing?: boolean;
}

export function DashboardLayout({
  children,
  merchantName = 'Merchant',
  isSyncing = false,
}: DashboardLayoutProps) {
  return (
    <div className="flex min-h-screen bg-gray-50 md:h-screen md:overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Header merchantName={merchantName} isSyncing={isSyncing} />
        <main className="flex-1 overflow-y-auto">
          <div className="max-w-7xl mx-auto px-4 md:px-8 py-5">{children}</div>
        </main>
      </div>
    </div>
  );
}
