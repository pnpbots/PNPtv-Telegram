# Alternative to supervisord for Railway deployment
web: python -m uvicorn payment_webhook:app --host 0.0.0.0 --port $PORT --workers 2
worker: python run_bot.py

