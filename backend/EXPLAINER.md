# EXPLAINER.md

## 1. The Ledger

**Balance calculation query:**

```python
totals = LedgerEntry.objects.filter(merchant=merchant).aggregate(
    available_balance=Sum("amount")
)
```

**Why I modeled credits and debits this way:**

I initially thought about separate `credits` and `debits` tables, but realized that would make balance calculation require two queries and a subtraction. With a single table and signed amounts (positive for credits, negative for holds), balance is just one `SUM()`. Simpler query, less room for bugs. The `BigIntegerField` in paise avoids floating-point rounding issues entirely. The unique constraint on `(merchant, reference)` gives me free deduplication via `IntegrityError` if something tries to create the same ledger entry twice. This design also guarantees that the ledger itself is the source of truth, and balances are never stored redundantly, eliminating reconciliation issues.

## 2. The Lock

**Exact code that prevents overdrawing:**

```python
with transaction.atomic():
    merchant_locked = (
        Merchant.objects
        .select_for_update(nowait=False)
        .get(id=merchant.id)
    )
    
    available_balance = (
        LedgerEntry.objects
        .filter(merchant=merchant_locked)
        .aggregate(balance=Sum("amount"))["balance"] or 0
    )

    if available_balance < amount_paise:
        return {"error": "Insufficient balance", "http_status": 400}
```

**Database primitive:** `SELECT FOR UPDATE` - row-level pessimistic lock. When two requests hit simultaneously, the first one locks the merchant row. The second one blocks until the first transaction commits. By the time the second request gets the lock, the first has already deducted the amount, so the balance check fails. This serializes the critical section at the database level, not in Python.

Locking the merchant row is sufficient because all balance calculations and ledger mutations are scoped to a single merchant. This avoids needing to lock the entire ledger table while still guaranteeing correctness.

## 3. The Idempotency

**How the system knows it has seen a key:**

Unique constraint on `(merchant, key)` in the `IdempotencyKey` table. The `get_or_create()` call is atomic - either it creates a new row or returns the existing one. If it returns existing, I know this key was used before.

**What happens if the first request is in-flight:**

```python
if not created:
    if idem_key.status == IdempotencyStatus.COMPLETED:
        return cached_response
    else:
        for retry_attempt in range(max_retries):
            time.sleep(50ms)
            idem_key = IdempotencyKey.objects.select_for_update().get(...)
            if idem_key.status == COMPLETED:
                return cached_response
        
        return {"status": "processing", "http_status": 409, ...}
```

The second request sees the key in `PROCESSING` state, waits up to 150ms polling for completion, and either returns the cached response (if first finished) or a 409 Conflict telling the client to retry. This avoids creating duplicate payouts while handling the race where the first request hasn't committed yet.

Idempotency keys expire after 24 hours. When an expired key is detected, I delete it and create a fresh record, allowing key reuse while maintaining uniqueness constraints.

## 4. The State Machine

**Where failed-to-completed is blocked:**

```python
def can_transition_to(self, target_status: str) -> bool:
    allowed = {
        PayoutStatus.PENDING: {PayoutStatus.PROCESSING, PayoutStatus.FAILED},
        PayoutStatus.PROCESSING: {PayoutStatus.COMPLETED, PayoutStatus.FAILED},
        PayoutStatus.COMPLETED: set(),
        PayoutStatus.FAILED: set(),
    }
    return target_status in allowed.get(self.status, set())
```

Both `COMPLETED` and `FAILED` have empty allowed sets. The enforcement happens inside `transition_payout_status()` where the row is locked using `select_for_update()` and the transition is validated before updating. This ensures validation and update happen atomically under a lock, preventing race conditions between concurrent workers.

**One thing I caught during testing:** I initially only set `processing_started_at` on the first `PENDING → PROCESSING` transition. But when a payout gets retried, it needs a fresh 30-second window for the scanner. So I changed it to refresh the timestamp on every entry to `PROCESSING`:

```python
if target_status == PayoutStatus.PROCESSING:
    payout_locked.processing_started_at = timezone.now()
    update_fields.append("processing_started_at")
```

## 5. The AI Audit

**What AI gave me (race condition):**

```python
available_balance = (
    LedgerEntry.objects.filter(merchant=merchant)
    .aggregate(balance=Sum("amount"))["balance"] or 0
)
if available_balance >= amount_paise:
    LedgerEntry.objects.create(
        merchant=merchant,
        amount=-amount_paise,
        reference=hold_reference,
    )
```

**What I caught:**

Running the concurrency test showed both requests passing the balance check and both creating ledger entries, resulting in negative balance. The check-then-deduct pattern without a lock is a classic race. Thread A reads balance=100, passes check. Thread B reads balance=100, passes check. Both deduct 60. Final balance=-20. Overdrawn.

**What I replaced it with:**

```python
with transaction.atomic():
    merchant_locked = Merchant.objects.select_for_update(nowait=False).get(id=merchant.id)
    available_balance = LedgerEntry.objects.filter(merchant=merchant_locked).aggregate(...)
    if available_balance < amount_paise:
        return error
    LedgerEntry.objects.create(
        merchant=merchant_locked,
        payout=payout,
        entry_type=LedgerEntry.EntryType.HOLD,
        amount=-amount_paise,
        reference=hold_reference,
    )
```

The `select_for_update()` forces serialization. Thread A locks merchant, checks balance, creates hold, commits. Thread B blocks until A commits, then reads the updated balance (now 40), fails the check, and gets rejected. Exactly one succeeds.

**Another thing I tightened:** The scanner was holding DB locks while calling `process_payout.apply_async()`, which is Redis I/O. I moved the enqueue outside the transaction:

```python
with transaction.atomic():
    stuck_payouts = list(Payout.objects.select_for_update(skip_locked=True).filter(...))
    retry_candidates.append((payout.id, payout.attempts))

for payout_id, attempts in retry_candidates:
    process_payout.apply_async(args=[payout_id], countdown=delay_seconds)
```

I also added `attempts` to the scanner index since the code branches on that field - better query plan.
