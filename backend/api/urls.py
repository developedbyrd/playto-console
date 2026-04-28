from django.urls import path

from api.views import BalanceView, BankAccountsView, PayoutRetryView, PayoutsView, TransactionsView

urlpatterns = [
    path("payouts/", PayoutsView.as_view(), name="payouts"),
    path("payouts/<str:payout_id>/retry/", PayoutRetryView.as_view(), name="payout-retry"),
    path("balance/", BalanceView.as_view(), name="balance"),
    path("transactions/", TransactionsView.as_view(), name="transactions"),
    path("bank-accounts/", BankAccountsView.as_view(), name="bank-accounts"),
]
