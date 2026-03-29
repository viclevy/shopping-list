from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    admin_password: str = "admin"
    port: int = 8080
    tls_enabled: bool = False
    tls_cert_file: str = ""
    tls_key_file: str = ""
    gemini_api_key: str = ""
    serpapi_key: str = ""
    data_dir: str = "./data"
    jwt_secret: str = ""
    jwt_expiry_hours: int = 720  # 30 days


settings = Settings()
