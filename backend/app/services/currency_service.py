import requests
from app.core.config import settings


class CurrencyService:
    def __init__(self):
        self.api_key = settings.EXCHANGE_RATE_API_KEY
        self.base_url = "https://api.exchangerate-api.com/v4/latest/USD"  # Using a free public API for demo

    def convert(self, amount, from_currency="USD", to_currency="EUR"):
        """
        Converts an amount from one currency to another.
        """
        try:
            # In a real app, you'd use the API key and handle different base currencies
            response = requests.get(self.base_url)
            data = response.json()

            rates = data.get("rates", {})
            if from_currency != "USD":
                # Convert to USD first if base is not USD
                amount = amount / rates.get(from_currency, 1)

            converted_amount = amount * rates.get(to_currency, 1)
            return {
                "original_amount": amount,
                "from": from_currency,
                "to": to_currency,
                "converted_amount": round(converted_amount, 2),
                "rate": rates.get(to_currency, 1),
                "success": True,
            }
        except Exception as e:
            return {"error": str(e), "success": False}


currency_service = CurrencyService()
