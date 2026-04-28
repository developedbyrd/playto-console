import logging

from rest_framework import status
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers import BalanceSerializer, BankAccountSerializer, CreatePayoutRequestSerializer, PayoutSerializer, TransactionSerializer
from api.services import ApiPayoutService
from merchants.services import MerchantService
from payouts.tasks import process_payout

logger = logging.getLogger(__name__)


class PayoutsView(APIView):
    authentication_classes = [BasicAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        merchant = MerchantService.get_merchant_for_user(request.user)
        if merchant is None:
            return Response({"error": "Merchant profile not found"}, status=status.HTTP_403_FORBIDDEN)

        idempotency_key = request.headers.get("Idempotency-Key")
        if not idempotency_key:
            return Response({"error": "Idempotency-Key header is required"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = CreatePayoutRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = ApiPayoutService.create_payout(
                merchant=merchant,
                idempotency_key=idempotency_key,
                amount_paise=serializer.validated_data["amount_paise"],
                bank_account_id=serializer.validated_data["bank_account_id"],
            )
            if result["payout"] and result["status"] in ("created",):
                process_payout.delay(result["payout"].id)
            return Response(result["response"], status=result["http_status"])
        except Exception:
            logger.exception("Unexpected error while creating payout")
            return Response(
                {"error": "Unable to process payout request"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def get(self, request):
        merchant = MerchantService.get_merchant_for_user(request.user)
        if merchant is None:
            return Response({"error": "Merchant profile not found"}, status=status.HTTP_403_FORBIDDEN)

        try:
            payouts = ApiPayoutService.list_payouts(merchant)
            data = PayoutSerializer(payouts, many=True).data
            return Response(data, status=status.HTTP_200_OK)
        except Exception:
            logger.exception("Unexpected error while listing payouts")
            return Response(
                {"error": "Unable to list payouts"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class BalanceView(APIView):
    authentication_classes = [BasicAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        merchant = MerchantService.get_merchant_for_user(request.user)
        if merchant is None:
            return Response({"error": "Merchant profile not found"}, status=status.HTTP_403_FORBIDDEN)

        try:
            balance = ApiPayoutService.get_balance(merchant)
            data = BalanceSerializer(balance).data
            return Response(data, status=status.HTTP_200_OK)
        except Exception:
            logger.exception("Unexpected error while fetching balance")
            return Response(
                {"error": "Unable to fetch balance"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class TransactionsView(APIView):
    authentication_classes = [BasicAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        merchant = MerchantService.get_merchant_for_user(request.user)
        if merchant is None:
            return Response({"error": "Merchant profile not found"}, status=status.HTTP_403_FORBIDDEN)

        try:
            transactions = ApiPayoutService.list_transactions(merchant)
            data = TransactionSerializer(transactions, many=True).data
            return Response(data, status=status.HTTP_200_OK)
        except Exception:
            logger.exception("Unexpected error while listing transactions")
            return Response(
                {"error": "Unable to list transactions"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class BankAccountsView(APIView):
    authentication_classes = [BasicAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        merchant = MerchantService.get_merchant_for_user(request.user)
        if merchant is None:
            return Response({"error": "Merchant profile not found"}, status=status.HTTP_403_FORBIDDEN)

        try:
            accounts = ApiPayoutService.list_bank_accounts(merchant)
            data = BankAccountSerializer(accounts, many=True).data
            return Response(data, status=status.HTTP_200_OK)
        except Exception:
            logger.exception("Unexpected error while listing bank accounts")
            return Response(
                {"error": "Unable to list bank accounts"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PayoutRetryView(APIView):
    authentication_classes = [BasicAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, payout_id):
        merchant = MerchantService.get_merchant_for_user(request.user)
        if merchant is None:
            return Response({"error": "Merchant profile not found"}, status=status.HTTP_403_FORBIDDEN)

        idempotency_key = request.headers.get("Idempotency-Key")
        if not idempotency_key:
            return Response({"error": "Idempotency-Key header is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from payouts.models import Payout, PayoutStatus
            old_payout = Payout.objects.get(id=int(payout_id), merchant=merchant, status=PayoutStatus.FAILED)

            result = ApiPayoutService.create_payout(
                merchant=merchant,
                idempotency_key=idempotency_key,
                amount_paise=old_payout.amount_paise,
                bank_account_id=old_payout.bank_account_id,
            )
            return Response(result["response"], status=result["http_status"])
        except Payout.DoesNotExist:
            return Response({"error": "Failed payout not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception:
            logger.exception("Unexpected error while retrying payout")
            return Response(
                {"error": "Unable to retry payout"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
