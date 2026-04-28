from django.conf import settings
from django.db import models


class Merchant(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="merchant_profile",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "merchants"

    def __str__(self) -> str:
        return f"Merchant<{self.id}> user={self.user_id}"


class MerchantBankAccount(models.Model):
    merchant = models.ForeignKey(
        Merchant,
        on_delete=models.CASCADE,
        related_name="bank_accounts",
    )
    account_name = models.CharField(max_length=100, default="Primary Account")
    bank_name = models.CharField(max_length=100, default="HDFC Bank")
    account_number = models.CharField(max_length=64)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "merchant_bank_accounts"
        constraints = [
            models.UniqueConstraint(
                fields=["merchant", "account_number"],
                name="uq_bank_account_per_merchant",
            ),
        ]
        indexes = [
            models.Index(fields=["merchant", "is_active"], name="idx_bankacct_merchant_active"),
            models.Index(fields=["merchant", "created_at"], name="idx_bankacct_merchant_created"),
        ]

    def __str__(self) -> str:
        return f"BankAccount<{self.id}> merchant={self.merchant_id}"
