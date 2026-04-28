import os
import django
import threading
import time
from uuid import uuid4

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Sum

from merchants.models import Merchant, MerchantBankAccount
from ledger.models import LedgerEntry
from payouts.models import Payout, IdempotencyKey, PayoutStatus, IdempotencyStatus
from payouts.services import PayoutService

User = get_user_model()


class PayoutConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='test_merchant', password='testpass123')
        self.merchant = Merchant.objects.create(user=self.user)
        self.bank_account = MerchantBankAccount.objects.create(
            merchant=self.merchant,
            account_name='Test Account',
            bank_name='Test Bank',
            account_number='ACC123',
            is_active=True,
            is_default=True
        )
        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type=LedgerEntry.EntryType.CREDIT,
            amount=100000,
            reference='credit'
        )

    def test_concurrent_same_idempotency_key(self):
        idempotency_key = str(uuid4())
        results = []
        errors = []
        
        def create_payout():
            try:
                result = PayoutService.create_payout_with_hold(
                    merchant=self.merchant,
                    amount_paise=5000,
                    bank_account_id=self.bank_account.id,
                    idempotency_key=idempotency_key
                )
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        threads = []
        for _ in range(5):
            t = threading.Thread(target=create_payout)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        self.assertEqual(len(errors), 0)
        
        payouts = Payout.objects.filter(idempotency_key=idempotency_key)
        self.assertEqual(payouts.count(), 1)
        
        payout = payouts.first()
        self.assertEqual(payout.amount_paise, 5000)
        
        ledger_entries = LedgerEntry.objects.filter(merchant=self.merchant, reference=f'payout:{payout.id}')
        self.assertEqual(ledger_entries.count(), 1)
        
        balance = LedgerEntry.objects.filter(merchant=self.merchant).aggregate(balance=Sum('amount'))['balance'] or 0
        self.assertEqual(balance, 95000)

    def test_concurrent_different_idempotency_keys(self):
        results = []
        errors = []
        
        def create_payout(idempotency_key):
            try:
                result = PayoutService.create_payout_with_hold(
                    merchant=self.merchant,
                    amount_paise=5000,
                    bank_account_id=self.bank_account.id,
                    idempotency_key=idempotency_key
                )
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        threads = []
        for i in range(5):
            idempotency_key = str(uuid4())
            t = threading.Thread(target=create_payout, args=(idempotency_key,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(results), 5)
        
        payouts = Payout.objects.filter(merchant=self.merchant)
        self.assertEqual(payouts.count(), 5)
        
        balance = LedgerEntry.objects.filter(merchant=self.merchant).aggregate(balance=Sum('amount'))['balance'] or 0
        self.assertEqual(balance, 75000)

    def test_concurrent_insufficient_balance(self):
        LedgerEntry.objects.all().delete()
        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type=LedgerEntry.EntryType.CREDIT,
            amount=10000,
            reference='credit'
        )
        
        results = []
        errors = []
        
        def create_payout(idempotency_key):
            try:
                result = PayoutService.create_payout_with_hold(
                    merchant=self.merchant,
                    amount_paise=7000,
                    bank_account_id=self.bank_account.id,
                    idempotency_key=idempotency_key
                )
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        threads = []
        for i in range(2):
            idempotency_key = str(uuid4())
            t = threading.Thread(target=create_payout, args=(idempotency_key,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(results), 2)
        
        created_count = sum(1 for r in results if r['status'] == 'created')
        failed_count = sum(1 for r in results if r['status'] == 'failed')
        
        self.assertEqual(created_count + failed_count, 2)
        
        payouts = Payout.objects.filter(merchant=self.merchant)
        self.assertEqual(payouts.count(), 1)
        
        balance = LedgerEntry.objects.filter(merchant=self.merchant).aggregate(balance=Sum('amount'))['balance'] or 0
        self.assertEqual(balance, 3000)


class PayoutIdempotencyTests(TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='test_merchant', password='testpass123')
        self.merchant = Merchant.objects.create(user=self.user)
        self.bank_account = MerchantBankAccount.objects.create(
            merchant=self.merchant,
            account_name='Test Account',
            bank_name='Test Bank',
            account_number='ACC123',
            is_active=True,
            is_default=True
        )
        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type=LedgerEntry.EntryType.CREDIT,
            amount=100000,
            reference='credit'
        )

    def test_idempotency_key_duplicate_request(self):
        idempotency_key = str(uuid4())
        
        result1 = PayoutService.create_payout_with_hold(
            merchant=self.merchant,
            amount_paise=5000,
            bank_account_id=self.bank_account.id,
            idempotency_key=idempotency_key
        )
        
        self.assertEqual(result1['status'], 'created')
        self.assertIsNotNone(result1['payout'])
        
        result2 = PayoutService.create_payout_with_hold(
            merchant=self.merchant,
            amount_paise=5000,
            bank_account_id=self.bank_account.id,
            idempotency_key=idempotency_key
        )
        
        self.assertEqual(result2['status'], 'duplicate')
        self.assertEqual(result1['payout'].id, result2['payout'].id)
        
        payouts = Payout.objects.filter(idempotency_key=idempotency_key)
        self.assertEqual(payouts.count(), 1)
        
        balance = LedgerEntry.objects.filter(merchant=self.merchant).aggregate(balance=Sum('amount'))['balance'] or 0
        self.assertEqual(balance, 95000)

    def test_idempotency_key_different_amounts(self):
        idempotency_key = str(uuid4())
        
        result1 = PayoutService.create_payout_with_hold(
            merchant=self.merchant,
            amount_paise=5000,
            bank_account_id=self.bank_account.id,
            idempotency_key=idempotency_key
        )
        
        result2 = PayoutService.create_payout_with_hold(
            merchant=self.merchant,
            amount_paise=7000,
            bank_account_id=self.bank_account.id,
            idempotency_key=idempotency_key
        )
        
        self.assertEqual(result2['status'], 'duplicate')
        self.assertEqual(result1['payout'].id, result2['payout'].id)
        self.assertEqual(result1['payout'].amount_paise, 5000)
        
        payouts = Payout.objects.filter(idempotency_key=idempotency_key)
        self.assertEqual(payouts.count(), 1)

    def test_idempotency_key_expiry(self):
        from django.utils import timezone
        from datetime import timedelta
        
        idempotency_key = str(uuid4())
        
        idem_key = IdempotencyKey.objects.create(
            merchant=self.merchant,
            key=idempotency_key,
            status=IdempotencyStatus.COMPLETED,
            http_status=200,
            response={'payout_id': 'old_payout'}
        )
        idem_key.expires_at = timezone.now() - timedelta(hours=25)
        idem_key.save()
        
        result = PayoutService.create_payout_with_hold(
            merchant=self.merchant,
            amount_paise=5000,
            bank_account_id=self.bank_account.id,
            idempotency_key=idempotency_key
        )
        
        self.assertEqual(result['status'], 'created')
        self.assertIsNotNone(result['payout'])
