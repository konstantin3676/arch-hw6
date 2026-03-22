from converters import UsdConverter


def main():
    try:
        amount = float(input("Введите значение в USD: \n"))

        currencies = [
            ("RUB", True),
            ("EUR", True),
            ("GBP", True),
            ("CNY", False),
        ]

        for currency, use_resilient in currencies:
            converter = UsdConverter(currency, use_resilient=use_resilient)
            result = converter.convert(amount)
            if result is not None:
                print(f"{amount} USD to {currency}: {result:.2f}")
            else:
                print(f"Unable to convert USD to {currency}. Rate unavailable.")

    except ValueError as e:
        print(f"Invalid input: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
