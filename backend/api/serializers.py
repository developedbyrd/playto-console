from rest_framework import serializers

from ledger.models import LedgerEntry
from merchants.models import MerchantBankAccount
from payouts.models import Payout


class BankAccountSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="pk", read_only=True)
    name = serializers.CharField(source="account_name", read_only=True)
    accountNumber = serializers.CharField(source="account_number", read_only=True)
    bankName = serializers.CharField(source="bank_name", read_only=True)

    class Meta:
        model = MerchantBankAccount
        fields = ["id", "name", "accountNumber", "bankName", "is_default"]


class TransactionSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()
    date = serializers.DateTimeField(source="created_at", read_only=True)
    amount = serializers.SerializerMethodField()

    class Meta:
        model = LedgerEntry
        fields = ["id", "amount", "reference", "type", "date"]

    def get_type(self, obj: LedgerEntry) -> str:
        return "credit" if obj.amount > 0 else "debit"

    def get_amount(self, obj: LedgerEntry) -> int:
        return obj.amount // 100


class PayoutSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="pk", read_only=True)
    amount = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    bankAccountId = serializers.CharField(source="bank_account_id", read_only=True)

    class Meta:
        model = Payout
        fields = [
            "id",
            "amount",
            "status",
            "createdAt",
            "bankAccountId",
        ]

    def get_amount(self, obj: Payout) -> int:
        return obj.amount_paise // 100


class CreatePayoutRequestSerializer(serializers.Serializer):
    amount_paise = serializers.IntegerField(min_value=1)
    bank_account_id = serializers.IntegerField(min_value=1)


class BalanceSerializer(serializers.Serializer):
    available_balance = serializers.IntegerField()
    held_balance = serializers.IntegerField()
    total_earnings = serializers.IntegerField()
