from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    admin_password: str = "admin"
    port: int = 8080
    tls_enabled: bool = False
    tls_cert_file: str = ""
    tls_key_file: str = ""
    gemini_api_key: str = ""
    gemini_model: str = "gemini-flash-latest"  # pinned names (e.g. gemini-2.5-flash) get retired for new projects
    receipt_provider: str = "gemini"  # which AI service reads receipt photos
    serpapi_key: str = ""
    data_dir: str = "./data"
    jwt_secret: str = ""
    jwt_expiry_hours: int = 2160  # 90 days (~3 months)


settings = Settings()
