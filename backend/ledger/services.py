from django.db.models import Sum

from ledger.models import LedgerEntry
from merchants.models import Merchant


class LedgerService:
    @staticmethod
    def get_available_balance(merchant: Merchant) -> int:
        return (
            LedgerEntry.objects.filter(merchant=merchant).aggregate(balance=Sum("amount"))["balance"] or 0
        )
