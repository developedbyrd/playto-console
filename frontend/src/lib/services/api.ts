import axios from 'axios';
import type { Balance, Payout, BankAccount, PayoutResponse, Transaction } from '../../lib/types';
import { generateIdempotencyKey } from '../../lib/api-utils';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

const AUTH_HEADER = 'Basic ' + btoa('merchant1:testpass123');

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    'Authorization': AUTH_HEADER,
  },
});

export async function fetchBalance(): Promise<Balance> {
  try {
    const response = await api.get('/balance/');
    const data = response.data;
    return {
      available: (data.available_balance || 0) / 100,
      held: (data.held_balance || 0) / 100,
      totalEarnings: (data.total_earnings || 0) / 100,
    };
  } catch (error: unknown) {
    console.error('[API] Balance fetch error:', error);
    throw new Error('Failed to fetch balance. Please try again.', { cause: error });
  }
}

export async function fetchPayouts(): Promise<Payout[]> {
  try {
    const response = await api.get('/payouts/');
    const data = response.data;
    return Array.isArray(data.data) ? data.data : Array.isArray(data) ? data : [];
  } catch (error: unknown) {
    console.error('[API] Payouts fetch error:', error);
    throw new Error('Failed to fetch payouts. Please try again.', { cause: error });
  }
}

export async function requestPayout(
  amount: number,
  bankAccountId: string,
  idempotencyKey?: string
): Promise<PayoutResponse> {
  const key = idempotencyKey || generateIdempotencyKey();

  try {
    const response = await api.post('/payouts/', {
      amount_paise: Math.round(amount * 100),
      bank_account_id: parseInt(bankAccountId),
    }, {
      headers: {
        'Idempotency-Key': key,
      },
    });

    const data = response.data;
    return data.data || data;
  } catch (error: unknown) {
    console.error('[API] Payout request error:', error);
    if (axios.isAxiosError(error) && error.response) {
      const errorData = error.response.data || {};
      const errorMessage = errorData.error || errorData.message || error.message;
      if (error.response.status === 400 && errorMessage.includes('balance')) {
        throw new Error('Insufficient balance', { cause: error });
      }
      throw new Error(errorMessage, { cause: error });
    }
    const message = error instanceof Error ? error.message : 'Failed to request payout';
    throw new Error(message, { cause: error });
  }
}

export async function retryPayout(payoutId: string): Promise<PayoutResponse> {
  const idempotencyKey = generateIdempotencyKey();

  try {
    const response = await api.post(`/payouts/${payoutId}/retry/`, {}, {
      headers: {
        'Idempotency-Key': idempotencyKey,
      },
    });

    const data = response.data;
    return data.data || data;
  } catch (error: unknown) {
    console.error('[API] Payout retry error:', error);
    if (axios.isAxiosError(error) && error.response) {
      const errorData = error.response.data || {};
      throw new Error(errorData.error || 'Failed to retry payout', { cause: error });
    }
    const message = error instanceof Error ? error.message : 'Failed to retry payout';
    throw new Error(message, { cause: error });
  }
}

export async function fetchTransactions(): Promise<Transaction[]> {
  try {
    const response = await api.get('/transactions/');
    const data = response.data;
    return Array.isArray(data.data) ? data.data : Array.isArray(data) ? data : [];
  } catch (error: unknown) {
    console.error('[API] Transactions fetch error:', error);
    throw new Error('Failed to fetch transactions. Please try again.', { cause: error });
  }
}

export async function fetchBankAccounts(): Promise<BankAccount[]> {
  try {
    const response = await api.get('/bank-accounts/');
    const data = response.data;
    return Array.isArray(data.data) ? data.data : Array.isArray(data) ? data : [];
  } catch (error: unknown) {
    console.error('[API] Bank accounts fetch error:', error);
    throw new Error('Failed to fetch bank accounts. Please try again.', { cause: error });
  }
}
