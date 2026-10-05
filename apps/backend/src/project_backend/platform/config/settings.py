"""Settings: parsed + validated here, injected by bootstrap. (blueprint 04 §7)

Business modules never read os.environ directly.
"""

from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

AppEnv = Literal["dev", "test", "staging", "production"]

# Usable only when app_env is dev/test; deployed environments must inject JWT_SECRET.
DEV_JWT_SECRET = "dev-only-jwt-secret-never-deploy-0000"
MIN_JWT_SECRET_BYTES = 32
DEPLOYED_ENVS: frozenset[str] = frozenset({"staging", "production"})


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: AppEnv = "dev"

    project_name: str = "project"
    version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/project"

    # begin capability:redis
    redis_url: str = "redis://localhost:6379/0"
    # end capability:redis

    # begin identity
    jwt_secret: SecretStr = SecretStr(DEV_JWT_SECRET)
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "project-api"
    jwt_audience: str = "project-clients"
    access_token_expire_minutes: int = 120

    @model_validator(mode="after")
    def _deployed_env_requires_real_secret(self) -> "Settings":
        if self.app_env in DEPLOYED_ENVS:
            secret = self.jwt_secret.get_secret_value()
            if secret == DEV_JWT_SECRET:
                raise ValueError(f"JWT_SECRET must be injected when APP_ENV={self.app_env}")
            if len(secret.encode("utf-8")) < MIN_JWT_SECRET_BYTES:
                raise ValueError(f"JWT_SECRET must be at least {MIN_JWT_SECRET_BYTES} bytes")
        return self

    # end identity

    cors_origins: list[str] = ["http://localhost:5173"]

    # Contracts source served by the app (contract-first: app.openapi() override).
    openapi_source_path: str = "contracts/http/openapi.yaml"

    @property
    def is_deployed(self) -> bool:
        return self.app_env in DEPLOYED_ENVS
