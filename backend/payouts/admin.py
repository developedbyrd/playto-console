from django.contrib import admin

from payouts.models import Payout, IdempotencyKey


@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    list_display = ("id", "merchant_id", "amount_paise", "status", "attempts", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("merchant__user__email", "idempotency_key")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)


@admin.register(IdempotencyKey)
class IdempotencyKeyAdmin(admin.ModelAdmin):
    list_display = ("id", "merchant_id", "key", "status", "http_status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("merchant__user__email", "key")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
