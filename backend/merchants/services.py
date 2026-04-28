from django.contrib.auth import get_user_model

from merchants.models import Merchant


class MerchantService:
    @staticmethod
    def get_merchant_for_user(user):
        if user is None or not getattr(user, "is_authenticated", False):
            return None
        return Merchant.objects.filter(user=user).first()

    @staticmethod
    def get_merchant_by_user_id(user_id: int):
        User = get_user_model()
        user = User.objects.filter(id=user_id).first()
        if user is None:
            return None
        return Merchant.objects.filter(user=user).first()
