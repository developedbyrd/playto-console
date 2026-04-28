'use client';

import { Avatar, AvatarFallback } from '../../components/ui/avatar';
import { ActivitySquare } from 'lucide-react';

interface HeaderProps {
  merchantName?: string;
  isSyncing?: boolean;
}

export function Header({ merchantName = 'Merchant', isSyncing = false }: HeaderProps) {
  return (
    <header className="bg-white border-b border-gray-200 h-16 sticky top-0 z-40">
      <div className="h-full px-8 flex items-center justify-between">
        <div className="flex items-center gap-2">
          {isSyncing && (
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <ActivitySquare className="w-4 h-4 animate-pulse text-indigo-600" />
              <span>Syncing...</span>
            </div>
          )}
        </div>

        <div className="flex items-center gap-4">
          <div className="text-right">
            <p className="text-sm font-semibold text-gray-900">{merchantName}</p>
            <p className="text-xs text-gray-500">Account Owner</p>
          </div>
          <Avatar className="h-10 w-10">
            <AvatarFallback className="bg-indigo-600 text-white">
              {merchantName.charAt(0).toUpperCase()}
            </AvatarFallback>
          </Avatar>
        </div>
      </div>
    </header>
  );
}
