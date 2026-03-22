import json
import logging
import os
import time
from abc import ABC, abstractmethod
from typing import Optional

import requests

DEFAULT_API_URL = "https://api.exchangerate-api.com/v4/latest/USD"
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 2
DEFAULT_CACHE_EXPIRY = 3600
DEFAULT_CACHE_FILE = "exchange_rates.json"
REQUEST_TIMEOUT = 10


class RateProvider(ABC):
    @abstractmethod
    def get_rate(self, currency: str) -> Optional[float]:
        pass


class CachedRateProvider(RateProvider):
    def __init__(
        self,
        api_url: str = DEFAULT_API_URL,
        cache_file: str = DEFAULT_CACHE_FILE,
        cache_expiry: int = DEFAULT_CACHE_EXPIRY,
    ):
        self.api_url = api_url
        self.cache_file = cache_file
        self.cache_expiry = cache_expiry
        self._rates: Optional[dict] = None

    def _load_from_cache(self) -> Optional[dict]:
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r") as f:
                    data = json.load(f)
                    if time.time() - data["timestamp"] < self.cache_expiry:
                        return data["rates"]
            except (json.JSONDecodeError, KeyError, IOError):
                pass
        return None

    def _save_to_cache(self, rates: dict) -> None:
        try:
            data = {"timestamp": time.time(), "rates": rates}
            with open(self.cache_file, "w") as f:
                json.dump(data, f)
        except IOError as e:
            logging.warning(f"Error saving to cache: {e}")

    def _fetch_rates(self) -> Optional[dict]:
        try:
            response = requests.get(self.api_url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            return data.get("rates")
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching rates from API: {e}")
            return None
        except (json.JSONDecodeError, KeyError) as e:
            logging.error(f"Error processing JSON response: {e}")
            return None

    def get_rate(self, currency: str) -> Optional[float]:
        if self._rates is None:
            self._rates = self._load_from_cache()
            if self._rates is None:
                self._rates = self._fetch_rates()
                if self._rates:
                    self._save_to_cache(self._rates)

        if self._rates:
            return self._rates.get(currency)
        return None


class ResilientRateProvider(CachedRateProvider):
    def __init__(
        self,
        api_url: str = DEFAULT_API_URL,
        cache_file: str = DEFAULT_CACHE_FILE,
        cache_expiry: int = DEFAULT_CACHE_EXPIRY,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay: int = DEFAULT_RETRY_DELAY,
    ):
        super().__init__(api_url, cache_file, cache_expiry)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger(__name__)
        if not logger.handlers:
            logger.setLevel(logging.INFO)
            ch = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
            ch.setFormatter(formatter)
            logger.addHandler(ch)
        return logger

    def _fetch_rates(self) -> Optional[dict]:
        for attempt in range(self.max_retries):
            try:
                response = requests.get(self.api_url, timeout=REQUEST_TIMEOUT)
                response.raise_for_status()
                data = response.json()
                rates = data.get("rates")
                if rates:
                    return rates
            except requests.exceptions.RequestException as e:
                self.logger.error(
                    f"Request failed (attempt {attempt + 1}/{self.max_retries}): {e}"
                )
            except (json.JSONDecodeError, KeyError) as e:
                self.logger.error(f"Error processing JSON response: {e}")

            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay)

        self.logger.error("Max retries reached. Unable to fetch rates.")
        return None


class CurrencyConverter(ABC):
    def __init__(self, rate_provider: RateProvider):
        self._rate_provider = rate_provider

    @property
    @abstractmethod
    def target_currency(self) -> str:
        pass

    def convert(self, amount: float) -> Optional[float]:
        if amount < 0:
            raise ValueError("Amount must be non-negative")

        rate = self._rate_provider.get_rate(self.target_currency)
        if rate is None:
            return None

        return amount * rate
