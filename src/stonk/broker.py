"""Read-only paper account connection. No order submission is exposed."""

import os


def paper_account_summary() -> dict:
    key = os.environ.get("ALPACA_API_KEY", "").strip()
    secret = os.environ.get("ALPACA_SECRET_KEY", "").strip()
    if not key or not secret:
        raise ValueError("Set ALPACA_API_KEY and ALPACA_SECRET_KEY to paper credentials")
    try:
        from alpaca.trading.client import TradingClient
    except ImportError as exc:
        raise ValueError('Install the paper extra: pip install -e ".[paper]"') from exc
    account = TradingClient(api_key=key, secret_key=secret, paper=True).get_account()
    return {
        "mode": "paper",
        "status": str(account.status),
        "equity": str(account.equity),
        "buying_power": str(account.buying_power),
        "trading_blocked": bool(account.trading_blocked),
    }
