'use client';

import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { formatCurrency, formatDate } from '../../lib/api-utils';
import type { Payout } from '../../lib/types';
import { StatusBadge } from './StatusBadge';
import { TableRowSkeleton } from './SkeletonLoader';
import { EmptyState } from './EmptyState';
import { retryPayout } from '../../lib/services/api';
import { toast } from 'sonner';
import { Inbox, RotateCw } from 'lucide-react';
import { useState } from 'react';

interface PayoutHistoryTableProps {
  payouts: Payout[];
  loading: boolean;
  onRetry: () => void;
}

export function PayoutHistoryTable({
  payouts,
  loading,
  onRetry,
}: PayoutHistoryTableProps) {
  const [retryingId, setRetryingId] = useState<string | null>(null);

  const handleRetry = async (payoutId: string) => {
    setRetryingId(payoutId);
    try {
      await retryPayout(payoutId);
      toast.success('Payout retry initiated');
      onRetry();
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to retry payout';
      toast.error(message);
    } finally {
      setRetryingId(null);
    }
  };

  if (loading) {
    return (
      <Card className="h-[17.1rem] bg-white border border-gray-200 rounded-xl overflow-y-auto">
        <div className="px-4 py-3">
          <h2 className="text-lg font-semibold text-gray-900">Payout History</h2>
          <div className="overflow-x-auto">
            <table className="w-full">
              <tbody>
                <TableRowSkeleton />
                <TableRowSkeleton />
                <TableRowSkeleton />
              </tbody>
            </table>
          </div>
        </div>
      </Card>
    );
  }

  if (payouts.length === 0) {
    return (
      <Card className="h-[17.1rem] bg-white border border-gray-200 rounded-xl overflow-y-auto p-0">
        <div className="px-4 py-3">
          <h2 className="text-lg font-semibold text-gray-900">Payout History</h2>
          <EmptyState
            icon={Inbox}
            title="No payouts yet"
            description="Your payout requests will appear here"
          />
        </div>
      </Card>
    );
  }

  const needsAction = payouts.some(p => p.status === 'failed' || p.status === 'processing');

  return (
    <Card className="h-[17.1rem] bg-white border border-gray-200 rounded-xl overflow-y-auto">
      <div className="px-4 py-3">
        <h2 className="text-lg font-semibold text-gray-900">Payout History</h2>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left px-6 py-3 text-xs font-semibold text-gray-600 uppercase">
                  Payout ID
                </th>
                <th className="text-left px-6 py-3 text-xs font-semibold text-gray-600 uppercase">
                  Amount
                </th>
                <th className="text-left px-6 py-3 text-xs font-semibold text-gray-600 uppercase">
                  Status
                </th>
                <th className="text-left px-6 py-3 text-xs font-semibold text-gray-600 uppercase">
                  Date
                </th>
                {needsAction && (
                  <th className="text-left px-6 py-3 text-xs font-semibold text-gray-600 uppercase">
                    Action
                  </th>
                )}
              </tr>
            </thead>
            <tbody>
              {payouts.map((payout) => (
                <tr key={payout.id} className="border-b border-gray-200 hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <span className="text-sm font-medium text-gray-900 font-mono">
                      {payout.id.slice(0, 8)}...
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-sm font-semibold text-gray-900">
                      {formatCurrency(payout.amount)}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <StatusBadge
                      status={payout.status}
                      failureReason={payout.failureReason}
                    />
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-sm text-gray-600">
                      {formatDate(payout.createdAt)}
                    </span>
                  </td>
                  {needsAction && (
                    <td className="px-6 py-4">
                      {payout.status === 'failed' ? (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleRetry(payout.id)}
                          disabled={retryingId === payout.id}
                          className="border-indigo-200 text-indigo-600 hover:bg-indigo-50 cursor-pointer"
                        >
                          {retryingId === payout.id ? (
                            <>
                              <RotateCw className="w-4 h-4 mr-1 animate-spin" />
                              Retrying
                            </>
                          ) : (
                            <>
                              <RotateCw className="w-4 h-4 mr-1" />
                              Retry
                            </>
                          )}
                        </Button>
                      ) : payout.status === 'processing' ? (
                        <span className="text-xs text-gray-500">
                          This payout is taking longer than expected
                        </span>
                      ) : null}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </Card>
  );
}
