from django.db.models import Sum

from ledger.models import LedgerEntry
from merchants.models import Merchant, MerchantBankAccount
from payouts.models import Payout, PayoutStatus
from payouts.query_services import PayoutQueryService
from payouts.services import PayoutService
from payouts.tasks import process_payout


class ApiPayoutService:
    @staticmethod
    def create_payout(
        merchant: Merchant,
        idempotency_key: str,
        amount_paise: int,
        bank_account_id: int,
    ) -> dict:
        result = PayoutService.create_payout_with_hold(
            merchant=merchant,
            amount_paise=amount_paise,
            bank_account_id=bank_account_id,
            idempotency_key=idempotency_key,
        )

        if result.get("status") == "created" and result.get("payout") is not None:
            process_payout.delay(result["payout"].id)

        return result

    @staticmethod
    def list_payouts(merchant: Merchant):
        return PayoutQueryService.list_for_merchant(merchant)

    @staticmethod
    def get_balance(merchant: Merchant) -> dict:
        totals = LedgerEntry.objects.filter(merchant=merchant).aggregate(
            available_balance=Sum("amount")
        )
        total_earnings = (
            LedgerEntry.objects.filter(merchant=merchant, amount__gt=0).aggregate(total=Sum("amount"))["total"] or 0
        )
        held_balance = (
            Payout.objects.filter(
                merchant=merchant,
                status__in=[PayoutStatus.PENDING, PayoutStatus.PROCESSING]
            ).aggregate(total=Sum("amount_paise"))["total"] or 0
        )
        return {
            "available_balance": totals["available_balance"] or 0,
            "held_balance": held_balance,
            "total_earnings": total_earnings,
        }

    @staticmethod
    def list_transactions(merchant: Merchant):
        return LedgerEntry.objects.filter(merchant=merchant).order_by("-created_at")

    @staticmethod
    def list_bank_accounts(merchant: Merchant):
        return MerchantBankAccount.objects.filter(merchant=merchant, is_active=True).order_by("-is_default", "-created_at")
