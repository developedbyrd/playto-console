from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from uuid import uuid4

from merchants.models import Merchant, MerchantBankAccount
from ledger.models import LedgerEntry
from payouts.models import Payout, PayoutStatus, IdempotencyKey, IdempotencyStatus

User = get_user_model()


class Command(BaseCommand):
    help = "Seed database with 2-3 merchants and credit ledger entries"

    def handle(self, *args, **options):
        with transaction.atomic():
            merchants_data = [
                {
                    "username": "merchant1",
                    "email": "merchant1@example.com",
                    "password": "testpass123",
                    "bank_accounts": [
                        {"number": "ACC0014242", "name": "Primary Savings", "bank": "HDFC Bank", "is_default": True},
                        {"number": "ACC0028899", "name": "Business Account", "bank": "ICICI Bank", "is_default": False},
                    ],
                    "ledger_credits": [10000000, 5000000],  # 100000 INR, 50000 INR
                },
                {
                    "username": "merchant2",
                    "email": "merchant2@example.com",
                    "password": "testpass123",
                    "bank_accounts": [
                        {"number": "ACC0031122", "name": "Current Account", "bank": "SBI", "is_default": True},
                    ],
                    "ledger_credits": [50000000],  # 500000 INR
                },
                {
                    "username": "merchant3",
                    "email": "merchant3@example.com",
                    "password": "testpass123",
                    "bank_accounts": [
                        {"number": "ACC0043344", "name": "Savings", "bank": "Axis Bank", "is_default": True},
                        {"number": "ACC0055566", "name": "Secondary", "bank": "Kotak Bank", "is_default": False},
                    ],
                    "ledger_credits": [7500000, 2500000],  # 75000 INR, 25000 INR
                },
            ]

            created_count = 0

            for data in merchants_data:
                if User.objects.filter(username=data["username"]).exists():
                    self.stdout.write(
                        self.style.WARNING(f"User {data['username']} already exists, skipping...")
                    )
                    continue

                user = User.objects.create_user(
                    username=data["username"],
                    email=data["email"],
                    password=data["password"],
                )

                merchant = Merchant.objects.create(user=user)

                for account_data in data["bank_accounts"]:
                    MerchantBankAccount.objects.create(
                        merchant=merchant,
                        account_name=account_data["name"],
                        bank_name=account_data["bank"],
                        account_number=account_data["number"],
                        is_active=True,
                        is_default=account_data.get("is_default", False),
                    )

                for idx, credit_amount in enumerate(data["ledger_credits"]):
                    LedgerEntry.objects.create(
                        merchant=merchant,
                        entry_type=LedgerEntry.EntryType.CREDIT,
                        amount=credit_amount,
                        reference=f"seed:{merchant.id}:{idx}",
                    )

                default_account = merchant.bank_accounts.filter(is_default=True).first()
                if default_account:
                    payout_amounts = [200000, 300000]
                    for payout_amount in payout_amounts:
                        idempotency_key = str(uuid4())
                        payout = Payout.objects.create(
                            merchant=merchant,
                            bank_account=default_account,
                            amount_paise=payout_amount,
                            status=PayoutStatus.COMPLETED,
                            idempotency_key=idempotency_key,
                            attempts=1,
                        )
                        LedgerEntry.objects.create(
                            merchant=merchant,
                            payout=payout,
                            entry_type=LedgerEntry.EntryType.HOLD,
                            amount=-payout_amount,
                            reference=f"payout:{payout.id}",
                        )
                        IdempotencyKey.objects.create(
                            merchant=merchant,
                            key=idempotency_key,
                            status=IdempotencyStatus.COMPLETED,
                            http_status=201,
                            response={"payout_id": payout.id, "status": "completed"},
                        )

                total_credit = sum(data["ledger_credits"])
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created merchant {data['username']} with "
                        f"{len(data['bank_accounts'])} bank account(s) and "
                        f"{len(data['ledger_credits'])} ledger credit(s) totaling {total_credit} paise"
                    )
                )
                created_count += 1

            self.stdout.write(
                self.style.SUCCESS(f"\nSuccessfully created {created_count} merchant(s)")
            )
