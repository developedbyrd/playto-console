from django.contrib import admin

from merchants.models import Merchant, MerchantBankAccount


@admin.register(Merchant)
class MerchantAdmin(admin.ModelAdmin):
    list_display = ("id", "user_id", "created_at")
    search_fields = ("user__username", "user__email")
    readonly_fields = ("created_at",)


@admin.register(MerchantBankAccount)
class MerchantBankAccountAdmin(admin.ModelAdmin):
    list_display = ("id", "merchant_id", "account_number", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("account_number", "merchant__user__username", "merchant__user__email")
    readonly_fields = ("created_at",)
