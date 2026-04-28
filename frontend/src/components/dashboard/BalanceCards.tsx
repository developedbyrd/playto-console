'use client';

import { Card } from '../../components/ui/card';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '../../components/ui/tooltip';
import { formatCurrency } from '../../lib/api-utils';
import type { Balance } from '../../lib/types';
import { Wallet, TrendingUp, Lock, AlertCircle } from 'lucide-react';
import { BalanceCardSkeleton } from './SkeletonLoader';

interface BalanceCardsProps {
  balance: Balance | null;
  loading: boolean;
}

export function BalanceCards({ balance, loading }: BalanceCardsProps) {
  if (loading || !balance) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <BalanceCardSkeleton />
        <BalanceCardSkeleton />
        <BalanceCardSkeleton />
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <Card className="bg-white border border-gray-200 rounded-xl px-4 py-3 h-38">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm font-medium text-gray-600 mb-2">Available Balance</p>
            <p className="text-3xl font-bold text-gray-900">
              {formatCurrency(balance.available)}
            </p>
          </div>
          <div className="p-2 bg-indigo-100 rounded-lg">
            <Wallet className="w-6 h-6 text-indigo-600" />
          </div>
        </div>
        <p className="text-xs text-gray-500 mt-4">Ready to withdraw</p>
      </Card>

      <TooltipProvider>
        <Card className="bg-white border border-gray-200 rounded-xl px-4 py-3 h-38">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <p className="text-sm font-medium text-gray-600">Held Balance</p>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <AlertCircle className="w-4 h-4 text-gray-400 cursor-help" />
                  </TooltipTrigger>
                  <TooltipContent className="max-w-xs">
                    <p>
                      Balance locked in pending payout requests. Released when processing
                      is complete.
                    </p>
                  </TooltipContent>
                </Tooltip>
              </div>
              <p className="text-3xl font-bold text-gray-900">
                {formatCurrency(balance.held)}
              </p>
            </div>
            <div className="p-2 bg-yellow-100 rounded-lg">
              <Lock className="w-6 h-6 text-yellow-600" />
            </div>
          </div>
          <p className="text-xs text-gray-500 mt-4">In pending payouts</p>
        </Card>
      </TooltipProvider>

      <Card className="bg-white border border-gray-200 rounded-xl px-4 py-3 h-38">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm font-medium text-gray-600 mb-2">Total Earnings</p>
            <p className="text-3xl font-bold text-gray-900">
              {formatCurrency(balance.totalEarnings)}
            </p>
          </div>
          <div className="p-2 bg-green-100 rounded-lg">
            <TrendingUp className="w-6 h-6 text-green-600" />
          </div>
        </div>
        <p className="text-xs text-gray-500 mt-4">All-time earnings</p>
      </Card>
    </div>
  );
}
