from django.db import models


class LedgerEntry(models.Model):
    class EntryType(models.TextChoices):
        CREDIT = "credit", "Credit"
        HOLD = "hold", "Hold"
        RELEASE = "release", "Release"

    merchant = models.ForeignKey(
        "merchants.Merchant",
        on_delete=models.PROTECT,
        related_name="ledger_entries",
    )
    payout = models.ForeignKey(
        "payouts.Payout",
        on_delete=models.PROTECT,
        related_name="ledger_entries",
        null=True,
        blank=True,
    )
    entry_type = models.CharField(
        max_length=16,
        choices=EntryType.choices,
        db_index=True,
    )
    amount = models.BigIntegerField()
    reference = models.CharField(max_length=128, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "ledger_entries"
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(amount=0),
                name="ck_ledger_amount_non_zero",
            ),
            models.UniqueConstraint(
                fields=["merchant", "reference"],
                name="uq_ledger_merchant_reference",
            ),
        ]
        indexes = [
            models.Index(fields=["merchant", "created_at"], name="idx_ledger_merchant_created"),
            models.Index(fields=["reference"], name="idx_ledger_reference"),
        ]

    def __str__(self) -> str:
        return f"LedgerEntry<{self.id}> merchant={self.merchant_id} amount={self.amount}"
