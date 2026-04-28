import logging
import random
from datetime import timedelta
from django.db import transaction, IntegrityError
from django.utils import timezone

from config.celery import app
from payouts.models import Payout, PayoutStatus
from payouts.services import PayoutService
from ledger.models import LedgerEntry

logger = logging.getLogger(__name__)
MAX_ATTEMPTS = 3


def _retry_delay_seconds(attempts: int) -> int:
    mapping = {1: 30, 2: 60, 3: 120}
    return mapping.get(attempts, 120)


PENDING_TIMEOUT_MINUTES = 5


@app.task(bind=True, autoretry_for=(), max_retries=0)
def process_payout(self, payout_id: int) -> dict:
    with transaction.atomic():
        payout = Payout.objects.select_for_update().get(id=payout_id)

        if payout.status in (PayoutStatus.COMPLETED, PayoutStatus.FAILED):
            logger.info(
                "Skipping payout processing because payout is already terminal: "
                "payout_id=%s status=%s",
                payout.id,
                payout.status,
            )
            return {"status": "skipped", "reason": "terminal", "payout_id": payout.id}

        if payout.status == PayoutStatus.PENDING:
            payout = PayoutService.transition_payout_status(
                payout,
                PayoutStatus.PROCESSING,
                already_locked=True,
            )
            logger.info("Payout transitioned pending->processing: payout_id=%s", payout.id)
        elif payout.status != PayoutStatus.PROCESSING:
            logger.warning(
                "Skipping payout due to unexpected status: payout_id=%s status=%s",
                payout.id,
                payout.status,
            )
            return {"status": "skipped", "reason": "invalid-status", "payout_id": payout.id}

        payout.attempts += 1
        payout.save(update_fields=["attempts"])
        logger.info("Incremented payout attempts: payout_id=%s attempts=%s", payout.id, payout.attempts)

        if payout.attempts >= MAX_ATTEMPTS:
            _refund_and_fail_locked(payout, reason="max-attempts-exceeded")
            return {"status": "failed", "reason": "max-attempts", "payout_id": payout.id}

        outcome_roll = random.randint(1, 100)
        if outcome_roll <= 70:
            payout = PayoutService.transition_payout_status(
                payout,
                PayoutStatus.COMPLETED,
                already_locked=True,
            )
            logger.info("Payout completed: payout_id=%s", payout.id)
            return {"status": "completed", "payout_id": payout.id}

        if outcome_roll <= 90:
            _refund_and_fail_locked(payout, reason="simulated-failure")
            return {"status": "failed", "reason": "simulated-failure", "payout_id": payout.id}

        logger.info("Payout left in processing (stuck simulation): payout_id=%s", payout.id)
        return {"status": "processing", "reason": "simulated-stuck", "payout_id": payout.id}


@app.task(bind=True, autoretry_for=(), max_retries=0)
def scan_and_retry_payouts(self) -> dict:
    cutoff = timezone.now() - timedelta(seconds=30)

    batch_size = 100

    retried = 0
    forced_failed = 0
    retry_candidates: list[tuple[int, int]] = []
    stuck_count = 0

    with transaction.atomic():
        stuck_payouts = list(
            Payout.objects
            .select_for_update(skip_locked=True)
            .filter(
                status=PayoutStatus.PROCESSING,
                processing_started_at__lte=cutoff,
            )
            .order_by("processing_started_at")[:batch_size]
        )

        if not stuck_payouts:
            logger.debug("Retry scanner found no stuck payouts.")
            return {"status": "ok", "stuck_count": 0, "retried": 0, "forced_failed": 0}

        stuck_count = len(stuck_payouts)

        logger.info(
            "Retry scanner detected stuck payouts: count=%s ids=%s",
            len(stuck_payouts),
            [p.id for p in stuck_payouts],
        )

        for payout in stuck_payouts:
            if payout.attempts >= MAX_ATTEMPTS:
                _refund_and_fail_locked(payout, reason="stuck-max-attempts")
                forced_failed += 1
                logger.warning(
                    "Forced fail for stuck payout after max attempts: payout_id=%s attempts=%s",
                    payout.id,
                    payout.attempts,
                )
                continue

            retry_candidates.append((payout.id, payout.attempts))

    for payout_id, attempts in retry_candidates:
        delay_seconds = _retry_delay_seconds(attempts)
        process_payout.apply_async(args=[payout_id], countdown=delay_seconds)
        retried += 1
        logger.info(
            "Scheduled payout retry with backoff: payout_id=%s attempts=%s delay_seconds=%s",
            payout_id,
            attempts,
            delay_seconds,
        )

    return {
        "status": "ok",
        "stuck_count": stuck_count,
        "retried": retried,
        "forced_failed": forced_failed,
    }


def _refund_and_fail_locked(payout: Payout, reason: str) -> None:
    refund_reference = f"refund:{payout.id}"

    try:
        refund_entry = LedgerEntry.objects.create(
            merchant=payout.merchant,
            payout=payout,
            entry_type=LedgerEntry.EntryType.RELEASE,
            amount=payout.amount_paise,
            reference=refund_reference,
        )
        logger.info(
            "Created refund ledger entry: payout_id=%s refund_entry_id=%s amount=%s reason=%s",
            payout.id,
            refund_entry.id,
            payout.amount_paise,
            reason,
        )
    except IntegrityError:
        logger.warning(
            "Refund already exists (deduplicated by unique reference): payout_id=%s reference=%s reason=%s",
            payout.id,
            refund_reference,
            reason,
        )

    payout = PayoutService.transition_payout_status(
        payout,
        PayoutStatus.FAILED,
        already_locked=True,
    )
    logger.info("Payout transitioned processing->failed: payout_id=%s reason=%s", payout.id, reason)


@app.task(bind=True, autoretry_for=(), max_retries=0)
def auto_fail_old_pending_payouts(self) -> dict:
    cutoff = timezone.now() - timedelta(minutes=PENDING_TIMEOUT_MINUTES)

    batch_size = 100
    failed_count = 0

    with transaction.atomic():
        old_pending = list(
            Payout.objects
            .select_for_update(skip_locked=True)
            .filter(
                status=PayoutStatus.PENDING,
                created_at__lte=cutoff,
            )
            .order_by("created_at")[:batch_size]
        )

        if not old_pending:
            logger.debug("No old pending payouts to auto-fail.")
            return {"status": "ok", "failed_count": 0}

        logger.info(
            "Auto-failing old pending payouts: count=%s ids=%s",
            len(old_pending),
            [p.id for p in old_pending],
        )

        for payout in old_pending:
            _refund_and_fail_locked(payout, reason=f"pending-timeout-{PENDING_TIMEOUT_MINUTES}min")
            failed_count += 1

    return {
        "status": "ok",
        "failed_count": failed_count,
    }
