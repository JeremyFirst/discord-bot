import re

def validate_steamid(value: str) -> str:
    value = value.strip()

    if re.fullmatch(r"STEAM_[0-5]:[01]:\d+", value):
        return value

    if re.fullmatch(r"\d{17}", value):
        return value

    raise ValueError("Неверный формат SteamID")


def clean_text(value: str, max_length: int) -> str:
    value = value.strip()

    if not value:
        raise ValueError("Поле не может быть пустым")

    if len(value) > max_length:
        raise ValueError(f"Максимальная длина — {max_length} символов")

    return value
