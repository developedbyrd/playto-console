'use client';

import { useState, useEffect, useCallback } from 'react';
import { DashboardLayout } from '../../components/dashboard/DashboardLayout';
import { PayoutHistoryTable } from '../../components/dashboard/PayoutHistoryTable';
import type { Payout } from '../../lib/types';
import { fetchPayouts } from '../../lib/services/api';
import { toast } from 'sonner';

export default function PayoutsPage() {
  const [payouts, setPayouts] = useState<Payout[]>([]);
  const [loading, setLoading] = useState(true);
  const [isSyncing, setIsSyncing] = useState(false);

  const loadPayouts = useCallback(async () => {
    try {
      const data = await fetchPayouts();
      setPayouts(data);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to fetch payouts';
      console.error('[Payouts] Fetch error:', error);
      if (!loading) {
        toast.error(message);
      }
    } finally {
      setLoading(false);
    }
  }, [loading]);

  useEffect(() => {
    const init = async () => {
      await loadPayouts();
    };
    init();

    const pollInterval = setInterval(() => {
      const poll = async () => {
        setIsSyncing(true);
        try {
          await loadPayouts();
        } catch (error) {
          console.error('[Payouts] Polling error:', error);
        } finally {
          setIsSyncing(false);
        }
      };

      poll();
    }, 5000);

    return () => clearInterval(pollInterval);
  }, [loadPayouts]);

  const handleRetry = () => {
    loadPayouts();
  };

  return (
    <DashboardLayout isSyncing={isSyncing}>
      <div className="space-y-5">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Payouts</h1>
          <p className="text-gray-600 mt-2">View and manage all your payout requests</p>
        </div>

        <PayoutHistoryTable payouts={payouts} loading={loading} onRetry={handleRetry} />
      </div>
    </DashboardLayout>
  );
}
