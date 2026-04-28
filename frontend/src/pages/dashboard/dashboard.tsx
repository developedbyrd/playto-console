import { useState, useEffect, useCallback } from 'react';
import { DashboardLayout } from '../../components/dashboard/DashboardLayout';
import { BalanceCards } from '../../components/dashboard/BalanceCards';
import { PayoutRequestCard } from '../../components/dashboard/PayoutRequestCard';
import { PayoutHistoryTable } from '../../components/dashboard/PayoutHistoryTable';
import { TransactionLedger } from '../../components/dashboard/TransactionLedger';
import type { Balance, Payout, BankAccount, Transaction } from '../../lib/types';
import { fetchBalance, fetchBankAccounts, fetchPayouts, fetchTransactions } from '../../lib/services/api';
import { toast } from 'sonner';



export default function DashboardPage() {
  const [balance, setBalance] = useState<Balance | null>(null);
  const [payouts, setPayouts] = useState<Payout[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [bankAccounts, setBankAccounts] = useState<BankAccount[]>([]);
  const [balanceLoading, setBalanceLoading] = useState(true);
  const [payoutsLoading, setPayoutsLoading] = useState(true);
  const [transactionsLoading, setTransactionsLoading] = useState(true);
  const [bankAccountsLoading, setBankAccountsLoading] = useState(true);
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncError, setSyncError] = useState<string | null>(null);
  const [lastSyncTime, setLastSyncTime] = useState<Date | null>(null);
  const [pollInterval, setPollInterval] = useState(5000);

  const loadBalance = useCallback(async () => {
    try {
      const data = await fetchBalance();
      setBalance(data);
      setSyncError(null);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to fetch balance';
      setSyncError(message);
      console.error('[Dashboard] Balance fetch error:', error);
      if (!balanceLoading) {
        toast.error(message);
      }
    } finally {
      setBalanceLoading(false);
    }
  }, [balanceLoading]);

  const loadPayouts = useCallback(async () => {
    try {
      const data = await fetchPayouts();
      setPayouts(data);
      setSyncError(null);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to fetch payouts';
      setSyncError(message);
      console.error('[Dashboard] Payouts fetch error:', error);
      if (!payoutsLoading) {
        toast.error(message);
      }
    } finally {
      setPayoutsLoading(false);
    }
  }, [payoutsLoading]);

  const loadTransactions = useCallback(async () => {
    try {
      const data = await fetchTransactions();
      setTransactions(data);
      setSyncError(null);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to fetch transactions';
      setSyncError(message);
      console.error('[Dashboard] Transactions fetch error:', error);
      if (!transactionsLoading) {
        toast.error(message);
      }
    } finally {
      setTransactionsLoading(false);
    }
  }, [transactionsLoading]);

  const loadBankAccounts = useCallback(async () => {
    try {
      const data = await fetchBankAccounts();
      setBankAccounts(data);
      setSyncError(null);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to fetch bank accounts';
      setSyncError(message);
      console.error('[Dashboard] Bank accounts fetch error:', error);
      if (!bankAccountsLoading) {
        toast.error(message);
      }
    } finally {
      setBankAccountsLoading(false);
    }
  }, [bankAccountsLoading]);

  useEffect(() => {
    const init = async () => {
      await Promise.all([loadBalance(), loadPayouts(), loadTransactions(), loadBankAccounts()]);
    };
    init();
  }, [loadBalance, loadPayouts, loadTransactions, loadBankAccounts]);

  useEffect(() => {
    const needsPolling = payouts.some(
      (p) => p.status === 'pending' || p.status === 'processing'
    );

    if (!needsPolling) {
      queueMicrotask(() => setPollInterval(5000));
      return;
    }

    const intervalId = setInterval(() => {
      const poll = async () => {
        setIsSyncing(true);
        try {
          await Promise.all([loadBalance(), loadPayouts()]);
          setLastSyncTime(new Date());
          
          const stillNeedsPolling = payouts.some(
            (p) => p.status === 'pending' || p.status === 'processing'
          );
          
          if (!stillNeedsPolling) {
            await Promise.all([loadTransactions(), loadBankAccounts()]);
          } else {
            queueMicrotask(() => setPollInterval((prev) => Math.min(prev * 1.5, 30000)));
          }
        } catch (error) {
          console.error('[Dashboard] Polling error:', error);
        } finally {
          setIsSyncing(false);
        }
      };

      poll();
    }, pollInterval);

    return () => clearInterval(intervalId);
  }, [payouts, pollInterval, loadBalance, loadPayouts, loadTransactions, loadBankAccounts]);

  const handlePayoutSuccess = () => {
    loadBalance();
    loadPayouts();
    loadTransactions();
    loadBankAccounts();
  };

  const handleRetry = () => {
    loadPayouts();
  };

  return (
    <DashboardLayout isSyncing={isSyncing}>
      <div className="space-y-5">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-600 mt-2">Manage your payouts and view transaction history</p>
          {lastSyncTime && (
            <p className="text-xs text-gray-500 mt-2">
              Last synced: {lastSyncTime.toLocaleTimeString()}
            </p>
          )}
        </div>

        <BalanceCards balance={balance} loading={balanceLoading} />

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-1">
            <PayoutRequestCard
              balance={balance}
              bankAccounts={bankAccounts}
              onPayoutSuccess={handlePayoutSuccess}
            />
          </div>

          <div className="lg:col-span-2">
            <PayoutHistoryTable
              payouts={payouts}
              loading={payoutsLoading}
              onRetry={handleRetry}
            />
          </div>
        </div>

        <TransactionLedger transactions={transactions} loading={transactionsLoading} />

        {syncError && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4">
            <p className="text-sm text-red-700">
              <span className="font-semibold">Sync Error:</span> {syncError}
            </p>
            <p className="text-xs text-red-600 mt-1">
              Please check your internet connection. We&apos;ll retry automatically.
            </p>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
