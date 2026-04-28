from merchants.models import Merchant
from payouts.models import Payout


class PayoutQueryService:
    @staticmethod
    def list_for_merchant(merchant: Merchant):
        return Payout.objects.filter(merchant=merchant).order_by("-created_at")
