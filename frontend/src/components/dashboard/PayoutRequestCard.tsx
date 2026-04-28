'use client';

import { useState } from 'react';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../components/ui/select';
import { formatCurrency } from '../../lib/api-utils';
import type { Balance, BankAccount } from '../../lib/types';
import { requestPayout } from '../../lib/services/api';
import { Spinner } from '../../components/ui/spinner';
import { toast } from 'sonner';

interface PayoutRequestCardProps {
  balance: Balance | null;
  bankAccounts: BankAccount[];
  onPayoutSuccess: () => void;
}

export function PayoutRequestCard({
  balance,
  bankAccounts,
  onPayoutSuccess,
}: PayoutRequestCardProps) {
  const [amount, setAmount] = useState('');
  const [selectedBankAccountId, setSelectedBankAccountId] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const availableBalance = balance?.available || 0;
  const amountNum = parseFloat(amount) || 0;
  const isInsufficientBalance = amountNum > 0 && amountNum > availableBalance;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!amount || !selectedBankAccountId) {
      setError('Please fill in all fields');
      return;
    }

    if (isInsufficientBalance) {
      setError(
        `Insufficient balance. Available: ${formatCurrency(availableBalance)}`
      );
      toast.error('Insufficient balance');
      return;
    }

    setIsSubmitting(true);

    try {
      await requestPayout(amountNum, selectedBankAccountId);
      toast.success('Payout requested successfully!');
      setAmount('');
      setSelectedBankAccountId('');
      onPayoutSuccess();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to request payout';
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Card className="bg-white border border-gray-200 rounded-xl px-4 py-3">
      <h2 className="text-lg font-semibold text-gray-900">Request Payout</h2>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Amount (₹)
          </label>
          <Input
            type="number"
            min="0"
            step="1"
            placeholder="Enter amount"
            value={amount}
            onChange={(e) => {
              setAmount(e.target.value);
              setError(null);
            }}
            disabled={isSubmitting}
            className="rounded-lg border-gray-300 focus:ring-1 focus:ring-gray-200 [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
          />
          {amount && (
            <p className="text-xs text-gray-500 mt-2">
              Available: {formatCurrency(availableBalance)}
            </p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Bank Account
          </label>
          <Select
            value={selectedBankAccountId}
            onValueChange={(value) => {
              setSelectedBankAccountId(value);
              setError(null);
            }}
            disabled={isSubmitting}
          >
            <SelectTrigger className="rounded-lg border-gray-300 focus:ring-1 focus:ring-gray-200 w-full cursor-pointer" hideIcon>
              <SelectValue placeholder="Select a bank account" />
            </SelectTrigger>
            <SelectContent>
              {bankAccounts.map((account) => (
                <SelectItem key={account.id} value={account.id}>
                  <span className="text-sm">
                    {account.name} • {account.bankName}
                  </span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {error && (
          <div className="rounded-lg bg-red-50 border border-red-200 p-3">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        <Button
          type="submit"
          disabled={isSubmitting || !amount || !selectedBankAccountId}
          className="w-full rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-2 cursor-pointer"
        >
          {isSubmitting ? (
            <>
              <Spinner className="mr-2" />
              Processing...
            </>
          ) : (
            'Request Payout'
          )}
        </Button>
      </form>
    </Card>
  );
}
