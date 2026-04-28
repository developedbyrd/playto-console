from datetime import timedelta

from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

UUID_REGEX = (
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-"
    r"[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
)


def default_expiry():
    return timezone.now() + timedelta(hours=24)


class PayoutStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PROCESSING = "processing", "Processing"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class IdempotencyStatus(models.TextChoices):
    PROCESSING = "PROCESSING", "Processing"
    COMPLETED = "COMPLETED", "Completed"


class Payout(models.Model):
    merchant = models.ForeignKey(
        "merchants.Merchant",
        on_delete=models.PROTECT,
        related_name="payouts",
    )
    bank_account = models.ForeignKey(
        "merchants.MerchantBankAccount",
        on_delete=models.PROTECT,
        related_name="payouts",
    )
    amount_paise = models.BigIntegerField()
    status = models.CharField(
        max_length=16,
        choices=PayoutStatus.choices,
        default=PayoutStatus.PENDING,
    )
    idempotency_key = models.CharField(
        max_length=36,
        validators=[RegexValidator(regex=UUID_REGEX, message="Must be a valid UUID")],
    )
    attempts = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processing_started_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "payouts"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount_paise__gt=0),
                name="ck_payout_amount_positive",
            ),
            models.UniqueConstraint(
                fields=["merchant", "idempotency_key"],
                name="uq_payout_merchant_idempotency",
            ),
        ]
        indexes = [
            models.Index(fields=["merchant", "status", "created_at"], name="idx_payout_m_status_cr"),
            models.Index(fields=["status", "created_at"], name="idx_payout_status_cr"),
            models.Index(fields=["status", "updated_at"], name="idx_payout_status_upd"),
            models.Index(fields=["status", "processing_started_at", "attempts"], name="idx_payout_status_proc_att"),
            models.Index(fields=["merchant", "created_at"], name="idx_payout_merchant_cr"),
        ]

    def can_transition_to(self, target_status: str) -> bool:
        allowed = {
            PayoutStatus.PENDING: {PayoutStatus.PROCESSING, PayoutStatus.FAILED},
            PayoutStatus.PROCESSING: {PayoutStatus.COMPLETED, PayoutStatus.FAILED},
            PayoutStatus.COMPLETED: set(),
            PayoutStatus.FAILED: set(),
        }
        return target_status in allowed.get(self.status, set())

    def __str__(self) -> str:
        return f"Payout<{self.id}> merchant={self.merchant_id} status={self.status}"


class IdempotencyKey(models.Model):
    merchant = models.ForeignKey(
        "merchants.Merchant",
        on_delete=models.CASCADE,
        related_name="idempotency_keys",
    )
    key = models.CharField(
        max_length=36,
        validators=[RegexValidator(regex=UUID_REGEX, message="Must be a valid UUID")],
    )
    status = models.CharField(
        max_length=16,
        choices=IdempotencyStatus.choices,
        default=IdempotencyStatus.PROCESSING,
    )
    response = models.JSONField(null=True, blank=True)
    http_status = models.PositiveSmallIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=default_expiry)

    class Meta:
        db_table = "idempotency_keys"
        constraints = [
            models.UniqueConstraint(
                fields=["merchant", "key"],
                name="uq_idem_merchant_key",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(status=IdempotencyStatus.PROCESSING, response__isnull=True, http_status__isnull=True)
                    | models.Q(status=IdempotencyStatus.COMPLETED, response__isnull=False, http_status__isnull=False)
                ),
                name="ck_idem_status_payload_consistency",
            ),
            models.CheckConstraint(
                condition=(models.Q(http_status__isnull=True) | models.Q(http_status__gte=100, http_status__lte=599)),
                name="ck_idem_http_status_range",
            ),
        ]
        indexes = [
            models.Index(fields=["status", "created_at"], name="idx_idem_status_created"),
            models.Index(fields=["merchant", "created_at"], name="idx_idem_merchant_created"),
            models.Index(fields=["expires_at"], name="idx_idem_expires"),
        ]

    def __str__(self) -> str:
        return f"IdempotencyKey<{self.id}> merchant={self.merchant_id} status={self.status}"
