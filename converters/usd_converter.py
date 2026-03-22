from converters.currency_converter import (
    CachedRateProvider,
    CurrencyConverter,
    ResilientRateProvider,
)


class UsdConverter(CurrencyConverter):
    def __init__(
        self, target_currency: str, rate_provider=None, use_resilient: bool = True
    ):
        if rate_provider is None:
            provider_class = (
                ResilientRateProvider if use_resilient else CachedRateProvider
            )
            rate_provider = provider_class()
        self._target_currency = target_currency
        super().__init__(rate_provider)

    @property
    def target_currency(self) -> str:
        return self._target_currency
