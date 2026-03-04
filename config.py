import os


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        raise RuntimeError(
            f"Missing required environment variable: {name}. "
            f"Set {name} before starting the application."
        )
    return value.strip()


def _optional_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _validate_database_url(value: str) -> str:
    if value.startswith("postgres://"):
        # Normalize shorthand DSN for SQLAlchemy compatibility.
        value = "postgresql://" + value[len("postgres://"):]

    supported_schemes = (
        "postgresql://",
        "postgresql+psycopg2://",
        "sqlite:///",
    )
    if not value.startswith(supported_schemes):
        raise RuntimeError(
            "Invalid DATABASE_URL. Expected one of: "
            "'postgresql://', 'postgresql+psycopg2://', or 'sqlite:///'."
        )
    return value


def _validate_redis_url(url: str | None) -> str | None:
    if not url:
        return None
    if not (url.startswith("redis://") or url.startswith("rediss://")):
        raise RuntimeError(
            "Invalid REDIS_URL. Expected a Redis URL starting with 'redis://' or 'rediss://'."
        )
    return url


def _validate_secret_key(value: str) -> str:
    if len(value) < 32:
        raise RuntimeError(
            "Invalid SECRET_KEY. SECRET_KEY must be at least 32 characters long."
        )
    return value


DATABASE_URL = _validate_database_url(_required_env("DATABASE_URL"))
REDIS_URL = _validate_redis_url(_optional_env("REDIS_URL"))
SECRET_KEY = _validate_secret_key(_required_env("SECRET_KEY"))
AZURE_SUBSCRIPTION_ID = _optional_env("AZURE_SUBSCRIPTION_ID")
AZURE_EXECUTION_RESOURCE_GROUP = _optional_env("AZURE_EXECUTION_RESOURCE_GROUP")
AZURE_LOCATION = _optional_env("AZURE_LOCATION")
