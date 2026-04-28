from django.contrib import admin

from ledger.models import LedgerEntry


@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    list_display = ("id", "merchant_id", "amount", "reference", "created_at")
    list_filter = ("created_at",)
    search_fields = ("reference", "merchant__user__username", "merchant__user__email")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
