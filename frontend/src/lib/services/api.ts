import axios from 'axios';
import type { Balance, Payout, BankAccount, PayoutResponse, Transaction } from '../../lib/types';
import { generateIdempotencyKey } from '../../lib/api-utils';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

const AUTH_HEADER = 'Basic ' + btoa('merchant1:testpass123');

// Simple in-memory cache for GET requests
const cache = new Map<string, { data: unknown; timestamp: number }>();
const CACHE_TTL = 5000; // 5 seconds

function getCached<T>(key: string): T | null {
  const entry = cache.get(key);
  if (entry && Date.now() - entry.timestamp < CACHE_TTL) {
    return entry.data as T;
  }
  cache.delete(key);
  return null;
}

function setCache(key: string, data: unknown): void {
  cache.set(key, { data, timestamp: Date.now() });
}

function clearCache(): void {
  cache.clear();
}

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    'Authorization': AUTH_HEADER,
  },
});

export async function fetchBalance(): Promise<Balance> {
  const cacheKey = 'balance';
  const cached = getCached<Balance>(cacheKey);
  if (cached) return cached;

  try {
    const response = await api.get('/balance/');
    const data = response.data;
    const result = {
      available: (data.available_balance || 0) / 100,
      held: (data.held_balance || 0) / 100,
      totalEarnings: (data.total_earnings || 0) / 100,
    };
    setCache(cacheKey, result);
    return result;
  } catch (error: unknown) {
    console.error('[API] Balance fetch error:', error);
    throw new Error('Failed to fetch balance. Please try again.', { cause: error });
  }
}

export async function fetchPayouts(): Promise<Payout[]> {
  const cacheKey = 'payouts';
  const cached = getCached<Payout[]>(cacheKey);
  if (cached) return cached;

  try {
    const response = await api.get('/payouts/');
    const data = response.data;
    const result = Array.isArray(data.data) ? data.data : Array.isArray(data) ? data : [];
    setCache(cacheKey, result);
    return result;
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
    clearCache(); // Clear cache after mutation
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
    clearCache(); // Clear cache after mutation
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
  const cacheKey = 'transactions';
  const cached = getCached<Transaction[]>(cacheKey);
  if (cached) return cached;

  try {
    const response = await api.get('/transactions/');
    const data = response.data;
    const result = Array.isArray(data.data) ? data.data : Array.isArray(data) ? data : [];
    setCache(cacheKey, result);
    return result;
  } catch (error: unknown) {
    console.error('[API] Transactions fetch error:', error);
    throw new Error('Failed to fetch transactions. Please try again.', { cause: error });
  }
}

export async function fetchBankAccounts(): Promise<BankAccount[]> {
  const cacheKey = 'bankAccounts';
  const cached = getCached<BankAccount[]>(cacheKey);
  if (cached) return cached;

  try {
    const response = await api.get('/bank-accounts/');
    const data = response.data;
    const result = Array.isArray(data.data) ? data.data : Array.isArray(data) ? data : [];
    setCache(cacheKey, result);
    return result;
  } catch (error: unknown) {
    console.error('[API] Bank accounts fetch error:', error);
    throw new Error('Failed to fetch bank accounts. Please try again.', { cause: error });
  }
}
