import logging
import time
from django.db import transaction, IntegrityError
from django.db.models import F, Sum, Q
from django.utils import timezone
from django.core.cache import cache

from merchants.models import Merchant, MerchantBankAccount
from ledger.models import LedgerEntry
from payouts.models import Payout, IdempotencyKey, PayoutStatus, IdempotencyStatus

logger = logging.getLogger(__name__)


def invalidate_balance_cache(merchant_id: int) -> None:
    """Invalidate the balance cache for a merchant."""
    cache_key = f"merchant_balance:{merchant_id}"
    cache.delete(cache_key)


def invalidate_merchant_caches(merchant_id: int) -> None:
    """Invalidate all merchant-related caches."""
    cache.delete(f"merchant_balance:{merchant_id}")
    cache.delete(f"merchant_payouts:{merchant_id}")
    cache.delete(f"merchant_transactions:{merchant_id}")
    cache.delete(f"merchant_bank_accounts:{merchant_id}")


class PayoutService:
    @staticmethod
    def create_payout_with_hold(
        merchant: Merchant,
        amount_paise: int,
        bank_account_id: int,
        idempotency_key: str,
    ) -> dict:
        with transaction.atomic():
            merchant_locked = (
                Merchant.objects
                .select_for_update(nowait=False)
                .get(id=merchant.id)
            )

            try:
                bank_account = MerchantBankAccount.objects.get(
                    id=bank_account_id,
                    merchant=merchant_locked
                )
                if not bank_account.is_active:
                    raise MerchantBankAccount.DoesNotExist()
            except MerchantBankAccount.DoesNotExist:
                response_payload = {
                    "error": "Invalid or inactive bank account",
                }
                idem_key, created = IdempotencyKey.objects.get_or_create(
                    merchant=merchant_locked,
                    key=idempotency_key,
                    defaults={
                        "status": IdempotencyStatus.COMPLETED,
                        "http_status": 400,
                        "response": response_payload,
                    }
                )

                if not created:
                    if idem_key.status == IdempotencyStatus.COMPLETED:
                        payout = Payout.objects.filter(
                            merchant=merchant_locked,
                            idempotency_key=idempotency_key,
                        ).first()
                        return {
                            "payout": payout,
                            "status": "duplicate",
                            "http_status": idem_key.http_status,
                            "response": idem_key.response,
                        }

                    return {
                        "payout": None,
                        "status": "processing",
                        "http_status": 409,
                        "response": {
                            "message": "Request is still processing. Retry after a delay.",
                            "idempotency_key": idempotency_key,
                        },
                    }
                
                return {
                    "payout": None,
                    "status": "failed",
                    "http_status": 400,
                    "response": response_payload,
                }

            idem_key, created = IdempotencyKey.objects.get_or_create(
                merchant=merchant_locked,
                key=idempotency_key,
                defaults={
                    'status': IdempotencyStatus.PROCESSING,
                }
            )

            if not created:
                idem_key = (
                    IdempotencyKey.objects
                    .select_for_update(nowait=False)
                    .get(merchant=merchant_locked, key=idempotency_key)
                )

                if idem_key.expires_at < timezone.now():
                    idem_key.delete()
                    idem_key = IdempotencyKey.objects.create(
                        merchant=merchant_locked,
                        key=idempotency_key,
                        status=IdempotencyStatus.PROCESSING,
                    )
                elif idem_key.status == IdempotencyStatus.COMPLETED:
                    payout = Payout.objects.filter(
                        merchant=merchant_locked,
                        idempotency_key=idempotency_key
                    ).first()
                    return {
                        "payout": payout,
                        "status": "duplicate",
                        "http_status": idem_key.http_status,
                        "response": idem_key.response,
                    }
                else:
                    max_retries = 3
                    retry_delay_ms = 50
                    
                    for retry_attempt in range(max_retries):
                        time.sleep(retry_delay_ms / 1000.0)
                        idem_key = (
                            IdempotencyKey.objects
                            .select_for_update(nowait=False)
                            .get(id=idem_key.id)
                        )
                        
                        if idem_key.status == IdempotencyStatus.COMPLETED:
                            payout = Payout.objects.filter(
                                merchant=merchant_locked,
                                idempotency_key=idempotency_key
                            ).first()
                            return {
                                "payout": payout,
                                "status": "duplicate",
                                "http_status": idem_key.http_status,
                                "response": idem_key.response,
                            }
                    
                    return {
                        "payout": None,
                        "status": "processing",
                        "http_status": 409,
                        "response": {
                            "message": "Request is still processing. Retry after a delay.",
                            "idempotency_key": idempotency_key,
                        },
                    }

            available_balance = (
                LedgerEntry.objects
                .filter(merchant=merchant_locked)
                .aggregate(balance=Sum("amount"))["balance"] or 0
            )

            if available_balance < amount_paise:
                response_payload = {
                    "error": "Insufficient balance",
                    "available": available_balance,
                    "requested": amount_paise,
                }
                idem_key.status = IdempotencyStatus.COMPLETED
                idem_key.http_status = 400
                idem_key.response = response_payload
                idem_key.save()

                return {
                    "payout": None,
                    "status": "failed",
                    "http_status": 400,
                    "response": response_payload,
                }

            payout = Payout.objects.create(
                merchant=merchant_locked,
                bank_account=bank_account,
                amount_paise=amount_paise,
                status=PayoutStatus.PENDING,
                idempotency_key=idempotency_key,
                attempts=0,
            )

            hold_reference = f"payout:{payout.id}"
            try:
                ledger_hold = LedgerEntry.objects.create(
                    merchant=merchant_locked,
                    payout=payout,
                    entry_type=LedgerEntry.EntryType.HOLD,
                    amount=-amount_paise,
                    reference=hold_reference,
                )
                # Invalidate all caches since new payout affects everything
                invalidate_merchant_caches(merchant_locked.id)
            except IntegrityError as e:
                payout.status = PayoutStatus.FAILED
                payout.save()
                
                response_payload = {
                    "error": "Failed to create ledger hold (duplicate reference detected)",
                }
                idem_key.status = IdempotencyStatus.COMPLETED
                idem_key.http_status = 500
                idem_key.response = response_payload
                idem_key.save()
                
                return {
                    "payout": payout,
                    "status": "failed",
                    "http_status": 500,
                    "response": response_payload,
                }

            response_payload = {
                "payout_id": payout.id,
                "amount_paise": payout.amount_paise,
                "status": payout.status,
                "idempotency_key": payout.idempotency_key,
                "created_at": payout.created_at.isoformat(),
            }

            idem_key.status = IdempotencyStatus.COMPLETED
            idem_key.http_status = 201
            idem_key.response = response_payload
            idem_key.save()

            return {
                "payout": payout,
                "status": "created",
                "http_status": 201,
                "response": response_payload,
            }

    @staticmethod
    def transition_payout_status(
        payout: Payout,
        target_status: str,
        *,
        already_locked: bool = False,
    ) -> Payout:
        def _apply_transition(payout_locked: Payout) -> Payout:
            current_status = payout_locked.status

            if current_status == target_status:
                logger.debug(
                    f"Payout {payout_locked.id} already in status {current_status}; "
                    "skipping idempotent transition."
                )
                return payout_locked

            if not payout_locked.can_transition_to(target_status):
                logger.warning(
                    f"Invalid payout state transition: payout_id={payout_locked.id}, "
                    f"current={current_status}, target={target_status}. "
                    "This may indicate a logic bug or an attempt to corrupt the ledger."
                )
                raise ValueError(
                    f"Invalid payout state transition: {current_status} → {target_status}. "
                    f"This may indicate a logic bug or an attempt to corrupt the ledger."
                )

            payout_locked.status = target_status
            update_fields = ["status"]
            if target_status == PayoutStatus.PROCESSING:
                payout_locked.processing_started_at = timezone.now()
                update_fields.append("processing_started_at")
            payout_locked.save(update_fields=update_fields)

            # Invalidate all caches when status affects data
            if target_status in (PayoutStatus.COMPLETED, PayoutStatus.FAILED):
                invalidate_merchant_caches(payout_locked.merchant_id)

            logger.info(
                f"Payout state transitioned: payout_id={payout_locked.id}, "
                f"from={current_status}, to={target_status}"
            )
            return payout_locked

        if already_locked:
            return _apply_transition(payout)

        with transaction.atomic():
            payout_locked = Payout.objects.select_for_update().get(id=payout.id)
            return _apply_transition(payout_locked)

    @staticmethod
    def validate_transition(payout: Payout, target_status: str) -> bool:
        return payout.can_transition_to(target_status)
