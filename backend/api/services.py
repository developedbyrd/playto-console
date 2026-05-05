from django.db.models import Sum, Q
from django.core.cache import cache

from ledger.models import LedgerEntry
from merchants.models import Merchant, MerchantBankAccount
from payouts.models import Payout, PayoutStatus
from payouts.query_services import PayoutQueryService
from payouts.services import PayoutService, invalidate_merchant_caches
from payouts.tasks import process_payout

CACHE_TTL_SECONDS = 60  # Cache for 60 seconds to reduce DB queries


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
            # Invalidate all caches since new payout affects everything
            invalidate_merchant_caches(merchant.id)

        return result

    @staticmethod
    def list_payouts(merchant: Merchant):
        cache_key = f"merchant_payouts:{merchant.id}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        result = PayoutQueryService.list_for_merchant(merchant)
        cache.set(cache_key, result, CACHE_TTL_SECONDS)
        return result

    @staticmethod
    def get_balance(merchant: Merchant) -> dict:
        cache_key = f"merchant_balance:{merchant.id}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        # Single query for all ledger data using conditional aggregation
        ledger_data = LedgerEntry.objects.filter(merchant=merchant).aggregate(
            available_balance=Sum("amount"),
            total_earnings=Sum("amount", filter=Q(amount__gt=0))
        )

        # Separate query for held balance (different table)
        held_balance = (
            Payout.objects.filter(
                merchant=merchant,
                status__in=[PayoutStatus.PENDING, PayoutStatus.PROCESSING]
            ).aggregate(total=Sum("amount_paise"))["total"] or 0
        )

        result = {
            "available_balance": ledger_data["available_balance"] or 0,
            "held_balance": held_balance,
            "total_earnings": ledger_data["total_earnings"] or 0,
        }
        cache.set(cache_key, result, CACHE_TTL_SECONDS)
        return result

    @staticmethod
    def list_transactions(merchant: Merchant):
        cache_key = f"merchant_transactions:{merchant.id}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        result = list(LedgerEntry.objects.filter(merchant=merchant).order_by("-created_at"))
        cache.set(cache_key, result, CACHE_TTL_SECONDS)
        return result

    @staticmethod
    def list_bank_accounts(merchant: Merchant):
        cache_key = f"merchant_bank_accounts:{merchant.id}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        result = list(MerchantBankAccount.objects.filter(merchant=merchant, is_active=True).order_by("-is_default", "-created_at"))
        cache.set(cache_key, result, CACHE_TTL_SECONDS)
        return result
