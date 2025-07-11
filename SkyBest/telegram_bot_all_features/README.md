# Telegram Bot Admin Dashboard

## To Run Locally
```bash
uvicorn dashboard.main:app --reload --port 8080
```

## To Deploy
You can deploy this on Render, Railway, or any VPS using FastAPI + Uvicorn.

## 🔁 Broadcast Integration

The bot now listens to POST requests at `/broadcast`:

**Example:**
```
curl -X POST https://<your-server>/broadcast \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello from admin panel!"}'
```

Set this as `BROADCAST_API` in your `.env` file for live integration with the admin dashboard.