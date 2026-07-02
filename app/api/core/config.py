from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # set from AEROBOTICS_API_TOKEN environment variable
    aerobotics_api_token: str
    aerobotics_base_url: str = "https://api.aerobotics.com/farming"

    # Row-clustering threshold as a fraction of the estimated row spacing
    row_spacing_threshold_multiplier: float = 0.4

settings = Settings()
