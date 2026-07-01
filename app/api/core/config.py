from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    aerobotics_api_token: str
    aerobotics_base_url: str = "https://api.aerobotics.com/farming"

    # Row-clustering threshold as a fraction of the estimated row spacing
    # (matches the value used in the reference notebook).
    row_spacing_threshold_multiplier: float = 0.4

    model_config = {"env_prefix": ""}


settings = Settings()
