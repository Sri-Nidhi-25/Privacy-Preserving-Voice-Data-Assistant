from app.config import settings


def validate_api_key(api_key: str) -> bool:
    return api_key == settings.API_KEY
