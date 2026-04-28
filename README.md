# Playto Console - Merchant Payout Management System

A production-ready payout management system for merchants with concurrency-safe payment processing, real-time balance tracking, and automated retry logic.

## Features

- **Ledger-Based Balance Tracking**: Single-table design with signed amounts (positive for credits, negative for holds) for accurate balance calculation
- **Concurrency-Safe Payouts**: Database-level row locking with `SELECT FOR UPDATE` prevents overdrawing and race conditions
- **Idempotency Handling**: UUID-based idempotency keys with 24-hour expiry, atomic `get_or_create` pattern, and polling for in-flight requests
- **State Machine Enforcement**: Strict payout status transitions (PENDING → PROCESSING → COMPLETED/FAILED) with validation at the database level
- **Automated Retry Scanner**: Celery beat scheduler detects stuck payouts, implements exponential backoff, and auto-fails after max attempts
- **Responsive Dashboard**: React frontend with mobile-first design, collapsible sidebar, and real-time updates
- **Real-Time Sync**: Automatic polling for pending/processing payouts with adaptive intervals

## Tech Stack

### Backend
- **Django 5.2** - Web framework
- **PostgreSQL** - Primary database
- **Celery 5.6** - Background task processing
- **Redis** - Message broker and result backend
- **Django REST Framework** - API layer

### Frontend
- **React 18** - UI framework
- **Vite** - Build tool
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **Lucide React** - Icons
- **Axios** - HTTP client

## Architecture Highlights

### Ledger Model
- Single `LedgerEntry` table with signed amounts
- `BigIntegerField` in paise avoids floating-point issues
- Unique constraint on `(merchant, reference)` for deduplication
- Entry types: CREDIT, HOLD, RELEASE

### Concurrency Control
- Row-level locking on merchant table during balance checks
- Atomic transactions for balance verification and hold creation
- Scanner releases DB locks before Redis I/O to minimize lock duration
- `processing_started_at` refreshed on every retry for accurate windows

### Idempotency
- Unique constraint on `(merchant, key)` in `IdempotencyKey` table
- Atomic `get_or_create` pattern under transaction
- 24-hour expiry with delete-and-recreate on expired keys
- Polling strategy (3 retries × 50ms) for in-flight requests

### State Machine
- Terminal states (COMPLETED, FAILED) have empty allowed transitions
- Enforcement in `transition_payout_status()` with `select_for_update()`
- Validation and update happen atomically under lock

## Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- Redis (or Redis Cloud)

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your database and Redis credentials
# DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT
# CELERY_BROKER_URL, CELERY_RESULT_BACKEND

# Run migrations
python manage.py migrate

# Seed sample data
python manage.py seed

# Start Django server
python manage.py runserver
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Copy environment template
cp .env.example .env

# Edit .env with your backend URL
# VITE_API_URL=http://localhost:8000

# Start development server
npm run dev
```

### Celery Setup

```bash
# Terminal 1: Start Celery worker
cd backend
celery -A config worker -l info -P solo --without-heartbeat --without-mingle

# Terminal 2: Start Celery beat scheduler
celery -A config beat -l info
```

## Environment Variables

### Backend (.env)
```
DEBUG=True
SECRET_KEY=your-secret-key
DB_NAME=playto_pay_system
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### Frontend (.env)
```
VITE_API_URL=http://localhost:8000
```

## Running the Application

1. Start PostgreSQL and Redis
2. Run backend: `python manage.py runserver`
3. Run frontend: `npm run dev` (in separate terminal)
4. Run Celery worker and beat (in separate terminals)
5. Access dashboard at `http://localhost:5173`

## API Endpoints

- `POST /api/payouts/` - Create payout request
- `GET /api/payouts/` - List payouts for merchant
- `GET /api/balance/` - Get merchant balance
- `GET /api/transactions/` - List ledger transactions
- `GET /api/bank-accounts/` - List bank accounts

## Testing

```bash
cd backend
pytest tests/ -v
```

## Project Structure

```
.
├── backend/
│   ├── api/              # REST API views and services
│   ├── config/           # Django settings and Celery config
│   ├── ledger/           # Ledger model and migrations
│   ├── merchants/        # Merchant and bank account models
│   ├── payouts/          # Payout models, services, tasks
│   └── tests/            # Test suites
├── frontend/
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── lib/          # Utilities and API client
│   │   └── pages/        # Page components
│   └── public/           # Static assets
└── README.md
```

## License

MIT
