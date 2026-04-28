'use client';

import { Card } from '../../components/ui/card';
import { formatCurrency, formatDate } from '../../lib/api-utils';
import type { Transaction } from '../../lib/types';
import { EmptyState } from './EmptyState';
import { BalanceCardSkeleton } from './SkeletonLoader';
import { ArrowDownCircle, ArrowUpCircle, Activity } from 'lucide-react';

interface TransactionLedgerProps {
  transactions: Transaction[];
  loading: boolean;
}

export function TransactionLedger({ transactions, loading }: TransactionLedgerProps) {
  if (loading) {
    return (
      <Card className="bg-white border border-gray-200 rounded-xl px-4 py-3">
        <h2 className="text-lg font-semibold text-gray-900">Recent Transactions</h2>
        <div className="space-y-3">
          <BalanceCardSkeleton />
          <BalanceCardSkeleton />
          <BalanceCardSkeleton />
        </div>
      </Card>
    );
  }

  if (transactions.length === 0) {
    return (
      <Card className="bg-white border border-gray-200 rounded-xl px-4 py-3">
        <h2 className="text-lg font-semibold text-gray-900">Recent Transactions</h2>
        <EmptyState
          icon={Activity}
          title="No transactions yet"
          description="Your transactions will appear here"
        />
      </Card>
    );
  }

  return (
    <Card className="bg-white border border-gray-200 rounded-xl px-4 py-3">
      <h2 className="text-lg font-semibold text-gray-900">Recent Transactions</h2>

      <div className="space-y-3">
        {transactions.slice(0, 10).map((transaction) => (
          <div
            key={transaction.id}
            className="flex items-center justify-between p-4 border border-gray-100 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <div className="flex items-center gap-4 flex-1">
              <div
                className={`p-2 rounded-lg ${
                  transaction.type === 'credit'
                    ? 'bg-green-100'
                    : 'bg-red-100'
                }`}
              >
                {transaction.type === 'credit' ? (
                  <ArrowDownCircle className="w-5 h-5 text-green-600" />
                ) : (
                  <ArrowUpCircle className="w-5 h-5 text-red-600" />
                )}
              </div>

              <div className="flex-1">
                <p className="text-sm font-semibold text-gray-900">
                  {transaction.reference}
                </p>
                <p className="text-xs text-gray-500">{formatDate(transaction.date)}</p>
              </div>
            </div>

            <p
              className={`text-sm font-semibold ${
                transaction.type === 'credit'
                  ? 'text-green-600'
                  : 'text-red-600'
              }`}
            >
              {transaction.type === 'credit' && '+'}
              {formatCurrency(transaction.amount)}
            </p>
          </div>
        ))}
      </div>
    </Card>
  );
}
