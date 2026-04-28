export interface Balance {
  available: number;
  held: number;
  totalEarnings: number;
}

export interface BankAccount {
  id: string;
  name: string;
  accountNumber: string;
  bankName: string;
}

export interface Payout {
  id: string;
  amount: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  createdAt: string;
  bankAccountId: string;
  failureReason?: string;
}

export interface Transaction {
  id: string;
  amount: number;
  type: 'credit' | 'debit';
  reference: string;
  date: string;
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
}

export interface PayoutResponse {
  id: string;
  amount: number;
  status: string;
  createdAt: string;
  bankAccountId: string;
}
