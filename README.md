# Instagram Feed Ingestion

A Python application to ingest and store Instagram feed data using the Instagram Graph API. Built with FastAPI, SQLAlchemy, and APScheduler.

## Features

- **OAuth Authentication** — Authenticate with Instagram via the Graph API OAuth flow
- **Feed Ingestion** — Fetch all media (images, videos, carousels) from authenticated accounts
- **Media Download** — Optionally download media files to local storage
- **Carousel Support** — Automatically fetches children of carousel/album posts
- **Scheduled Ingestion** — Automatic periodic feed ingestion via APScheduler
- **REST API** — Query ingested media with filtering and pagination
- **Multi-Account** — Support multiple Instagram accounts
- **Ingestion Logs** — Track ingestion history and errors

## Prerequisites

- Python 3.11+
- A [Facebook Developer](https://developers.facebook.com/) account
- An Instagram Basic Display API or Instagram Graph API app

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/gaurav-an-sre/instagram-feed-ingestion.git
cd instagram-feed-ingestion
```

### 2. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` with your Instagram app credentials:

| Variable | Description |
|----------|-------------|
| `INSTAGRAM_APP_ID` | Your Instagram/Facebook App ID |
| `INSTAGRAM_APP_SECRET` | Your Instagram/Facebook App Secret |
| `INSTAGRAM_REDIRECT_URI` | OAuth redirect URI (default: `http://localhost:8000/auth/callback`) |
| `DATABASE_URL` | SQLAlchemy database URL (default: SQLite) |
| `MEDIA_DOWNLOAD_DIR` | Directory for downloaded media files |
| `INGESTION_INTERVAL_MINUTES` | Auto-ingestion interval in minutes (default: 30) |

### 5. Run the application

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

## Docker

```bash
docker compose up --build
```

## API Endpoints

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/auth/login` | Get Instagram OAuth authorization URL |
| `GET` | `/auth/callback` | OAuth callback (handles token exchange) |
| `POST` | `/auth/token` | Manually set an access token |

### Feed

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/feed/media` | List ingested media (with pagination & filters) |
| `GET` | `/feed/media/{media_id}` | Get a specific media item |
| `POST` | `/feed/ingest/{user_id}` | Trigger ingestion for a specific account |
| `POST` | `/feed/ingest` | Trigger ingestion for all accounts |

### Accounts

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/accounts/` | List all connected accounts |
| `GET` | `/accounts/{user_id}` | Get account details |
| `DELETE` | `/accounts/{user_id}` | Remove an account |
| `GET` | `/accounts/{user_id}/logs` | View ingestion history |

### Status

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | API info |
| `GET` | `/status` | Application status (accounts, media count, scheduler) |

## Usage

### 1. Authenticate

Visit `http://localhost:8000/auth/login` to get the Instagram authorization URL. Complete the OAuth flow to connect your account.

Alternatively, if you already have an access token:

```bash
curl -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/json" \
  -d '{"access_token": "YOUR_TOKEN"}'
```

### 2. Ingest Feed

Trigger manual ingestion:

```bash
curl -X POST http://localhost:8000/feed/ingest/{instagram_user_id}
```

Or ingest all accounts:

```bash
curl -X POST http://localhost:8000/feed/ingest
```

The scheduler also runs automatic ingestion at the configured interval.

### 3. Query Media

```bash
curl "http://localhost:8000/feed/media?page=1&page_size=10&media_type=IMAGE"
```

## Running Tests

```bash
pip install pytest
pytest tests/ -v
```

## Project Structure

```
instagram-feed-ingestion/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── config.py             # Application settings
│   ├── database.py           # Database engine and session
│   ├── models/
│   │   └── instagram.py      # SQLAlchemy models
│   ├── schemas/
│   │   └── instagram.py      # Pydantic request/response schemas
│   ├── routers/
│   │   ├── auth.py           # Authentication endpoints
│   │   ├── feed.py           # Feed and ingestion endpoints
│   │   └── accounts.py       # Account management endpoints
│   └── services/
│       ├── instagram_client.py  # Instagram Graph API client
│       ├── ingestion.py         # Feed ingestion logic
│       └── scheduler.py        # APScheduler configuration
├── tests/
│   └── test_api.py           # API tests
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── .env.example
```

## License

MIT
