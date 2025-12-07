"""Configuration management system using pydantic-settings.

This module provides a comprehensive configuration system with:
- Environment variable loading from .env files
- YAML configuration file support with environment overrides
- Type validation using Pydantic
- Nested settings for different components
- Support for environment variable delimiter (__) for nested config
"""

from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProviderSettings(BaseSettings):
    """LLM Provider selection configuration."""

    model_config = SettingsConfigDict(
        env_prefix="LLM__", env_nested_delimiter="__", extra="ignore"
    )

    provider: str = Field(
        default="auto",
        description="LLM provider to use: 'openai', 'lmstudio', 'ollama', 'llamacpp', 'mlxlm', or 'auto' (auto-detect)",
    )

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        """Validate provider selection."""
        allowed = {"openai", "lmstudio", "ollama", "llamacpp", "mlxlm", "auto"}
        v_lower = v.lower()
        if v_lower not in allowed:
            raise ValueError(f"LLM provider must be one of {allowed}")
        return v_lower


class OpenAISettings(BaseSettings):
    """OpenAI API configuration."""

    model_config = SettingsConfigDict(
        env_prefix="OPENAI__", env_nested_delimiter="__", extra="ignore"
    )

    api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    model: str = Field(default="gpt-4o-mini", description="OpenAI model to use")
    max_tokens: int = Field(default=2048, description="Maximum tokens in response")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    timeout: int = Field(default=60, ge=1, description="Request timeout in seconds")


class LMStudioSettings(BaseSettings):
    """LM Studio configuration."""

    model_config = SettingsConfigDict(
        env_prefix="LM_STUDIO__", env_nested_delimiter="__", extra="ignore"
    )

    base_url: str = Field(
        default="http://localhost:1234/v1",
        description="Base URL for LM Studio API (OpenAI-compatible)",
    )
    api_key: str = Field(default="not-needed", description="API key (not needed for LM Studio)")
    model_name: str = Field(default="local-model", description="Model name to use")
    max_tokens: int = Field(default=2048, description="Maximum tokens in response")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    timeout: int = Field(default=30, ge=1, description="Request timeout in seconds")


class OllamaSettings(BaseSettings):
    """Ollama configuration.

    Environment variables use OLLAMA__ prefix.
    Example: OLLAMA__BASE_URL=http://localhost:11434/v1
    """

    model_config = SettingsConfigDict(
        env_prefix="OLLAMA__", env_nested_delimiter="__", extra="ignore"
    )

    base_url: str = Field(
        default="http://localhost:11434/v1",
        description="Base URL for Ollama API (OpenAI-compatible endpoint)",
    )
    api_key: str = Field(
        default="ollama",
        description="API key (Ollama accepts any value)",
    )
    model_name: str = Field(
        default="llama3.2",
        description="Default model to use",
    )
    max_tokens: int = Field(
        default=2048,
        description="Maximum tokens in response",
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature",
    )
    timeout: int = Field(
        default=60,
        ge=1,
        description="Request timeout in seconds",
    )
    # Ollama-specific settings
    num_ctx: int = Field(
        default=4096,
        description="Context window size",
    )
    num_parallel: int = Field(
        default=2,
        description="Number of parallel requests Ollama can handle",
    )


class LlamaCppSettings(BaseSettings):
    """llama.cpp server configuration.

    Environment variables use LLAMACPP__ prefix.
    Example: LLAMACPP__BASE_URL=http://localhost:8080/v1
    """

    model_config = SettingsConfigDict(
        env_prefix="LLAMACPP__", env_nested_delimiter="__", extra="ignore"
    )

    base_url: str = Field(
        default="http://localhost:8080/v1",
        description="Base URL for llama.cpp server (OpenAI-compatible endpoint)",
    )
    api_key: str = Field(
        default="not-needed",
        description="API key (not required for llama.cpp)",
    )
    model_name: str = Field(
        default="local-model",
        description="Model identifier (used for logging/display)",
    )
    max_tokens: int = Field(
        default=2048,
        description="Maximum tokens in response",
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature",
    )
    timeout: int = Field(
        default=120,
        ge=1,
        description="Request timeout in seconds (longer for large models)",
    )
    # llama.cpp-specific settings
    n_gpu_layers: int = Field(
        default=-1,
        description="Number of GPU layers (-1 for all available)",
    )
    ctx_size: int = Field(
        default=8192,
        description="Context window size",
    )
    n_threads: int = Field(
        default=4,
        description="Number of CPU threads to use",
    )


class MlxLmSettings(BaseSettings):
    """MLX-LM server configuration.

    Environment variables use MLXLM__ prefix.
    Example: MLXLM__BASE_URL=http://localhost:8081/v1

    MLX-LM runs on macOS host with Metal GPU acceleration.
    Server command: mlx_lm.server --model <model> --port 8081
    """

    model_config = SettingsConfigDict(
        env_prefix="MLXLM__", env_nested_delimiter="__", extra="ignore"
    )

    base_url: str = Field(
        default="http://localhost:8081/v1",
        description="Base URL for MLX-LM server (OpenAI-compatible endpoint)",
    )
    api_key: str = Field(
        default="not-needed",
        description="API key (not required for MLX-LM)",
    )
    model_name: str = Field(
        default="local-model",
        description="Model identifier (used for logging/display)",
    )
    max_tokens: int = Field(
        default=2048,
        description="Maximum tokens in response",
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature",
    )
    timeout: int = Field(
        default=120,
        ge=1,
        description="Request timeout in seconds",
    )


class DatabaseSettings(BaseSettings):
    """PostgreSQL database configuration."""

    model_config = SettingsConfigDict(env_prefix="DATABASE__", env_nested_delimiter="__")

    url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/mai_framework",
        description="PostgreSQL connection URL with asyncpg driver",
    )
    pool_size: int = Field(default=20, ge=1, description="Connection pool size")
    max_overflow: int = Field(default=10, ge=0, description="Maximum overflow connections")
    pool_timeout: int = Field(default=30, ge=1, description="Connection pool timeout in seconds")
    echo: bool = Field(default=False, description="Echo SQL statements (debug)")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Ensure asyncpg driver is used."""
        if not v.startswith("postgresql+asyncpg://"):
            raise ValueError("Database URL must use asyncpg driver: postgresql+asyncpg://")
        return v


class RedisSettings(BaseSettings):
    """Redis configuration."""

    model_config = SettingsConfigDict(env_prefix="REDIS__", env_nested_delimiter="__")

    url: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")
    max_connections: int = Field(default=50, ge=1, description="Maximum connections in pool")
    timeout: int = Field(default=5, ge=1, description="Connection timeout in seconds")
    decode_responses: bool = Field(
        default=True, description="Decode responses to strings automatically"
    )


class QdrantSettings(BaseSettings):
    """Qdrant vector store configuration."""

    model_config = SettingsConfigDict(env_prefix="QDRANT__", env_nested_delimiter="__")

    url: str = Field(default="http://localhost:6333", description="Qdrant server URL")
    api_key: Optional[str] = Field(default=None, description="Qdrant API key (optional)")
    collection_name: str = Field(
        default="mai_embeddings", description="Default collection name for embeddings"
    )
    vector_size: int = Field(default=1536, ge=1, description="Embedding vector size")
    distance_metric: str = Field(
        default="Cosine", description="Distance metric (Cosine, Dot, Euclidean)"
    )

    @field_validator("distance_metric")
    @classmethod
    def validate_distance_metric(cls, v: str) -> str:
        """Validate distance metric."""
        allowed = {"Cosine", "Dot", "Euclidean"}
        if v not in allowed:
            raise ValueError(f"Distance metric must be one of {allowed}")
        return v


class JWTSettings(BaseSettings):
    """JWT authentication configuration."""

    model_config = SettingsConfigDict(env_prefix="JWT__", env_nested_delimiter="__")

    secret: str = Field(
        default="your-secret-key-change-this-in-production",
        description="Secret key for signing tokens",
    )
    algorithm: str = Field(default="HS256", description="JWT signing algorithm")
    access_token_expire_minutes: int = Field(
        default=30, ge=1, description="Access token expiration in minutes"
    )
    refresh_token_expire_days: int = Field(
        default=7, ge=1, description="Refresh token expiration in days"
    )


class MemorySettings(BaseSettings):
    """Memory management configuration."""

    model_config = SettingsConfigDict(env_prefix="MEMORY__", env_nested_delimiter="__")

    short_term_ttl: int = Field(default=3600, ge=1, description="Short-term memory TTL in seconds")
    long_term_enabled: bool = Field(default=True, description="Enable long-term memory")
    semantic_search_enabled: bool = Field(default=True, description="Enable semantic search")
    max_history: int = Field(
        default=50, ge=1, description="Maximum conversation history to maintain"
    )


class ToolSettings(BaseSettings):
    """Tool system configuration."""

    model_config = SettingsConfigDict(env_prefix="TOOL__", env_nested_delimiter="__")

    timeout: int = Field(default=30, ge=1, description="Default tool execution timeout in seconds")
    max_retries: int = Field(default=3, ge=0, description="Maximum retry attempts")
    cache_enabled: bool = Field(default=True, description="Enable tool result caching")
    cache_ttl: int = Field(default=300, ge=0, description="Cache TTL in seconds")


class PipelineSettings(BaseSettings):
    """Pipeline orchestration configuration."""

    model_config = SettingsConfigDict(env_prefix="PIPELINE__", env_nested_delimiter="__")

    max_parallel: int = Field(default=5, ge=1, description="Maximum parallel executions")
    timeout: int = Field(default=300, ge=1, description="Pipeline execution timeout in seconds")


class RateLimitSettings(BaseSettings):
    """Rate limiting configuration."""

    model_config = SettingsConfigDict(env_prefix="RATE_LIMIT__", env_nested_delimiter="__")

    enabled: bool = Field(default=True, description="Enable rate limiting")
    requests: int = Field(default=100, ge=1, description="Number of requests allowed")
    period: int = Field(default=60, ge=1, description="Time period in seconds")


class MetricsSettings(BaseSettings):
    """Observability and metrics configuration."""

    model_config = SettingsConfigDict(env_prefix="METRICS__", env_nested_delimiter="__")

    enabled: bool = Field(default=True, description="Enable Prometheus metrics")
    port: int = Field(default=9090, ge=1024, le=65535, description="Metrics server port")


class SentrySettings(BaseSettings):
    """Sentry error tracking configuration."""

    model_config = SettingsConfigDict(env_prefix="SENTRY__", env_nested_delimiter="__")

    dsn: Optional[str] = Field(default=None, description="Sentry DSN")
    environment: str = Field(default="development", description="Environment name")
    traces_sample_rate: float = Field(
        default=0.1, ge=0.0, le=1.0, description="Traces sample rate"
    )


class Settings(BaseSettings):
    """Main application settings.

    This is the root configuration class that aggregates all component settings.
    Settings are loaded from:
    1. Environment variables (highest priority)
    2. .env file
    3. YAML config file (if provided)
    4. Default values (lowest priority)
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
        case_sensitive=False,
    )

    # Application settings
    app_name: str = Field(default="mai-framework", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    environment: str = Field(default="development", description="Environment (development/production)")
    debug: bool = Field(default=True, description="Debug mode")
    log_level: str = Field(default="INFO", description="Logging level")

    # API settings
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, ge=1024, le=65535, description="API port")
    api_workers: int = Field(default=1, ge=1, description="Number of API workers")
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins",
    )

    # Component settings (nested)
    llm: LLMProviderSettings = Field(default_factory=LLMProviderSettings)
    openai: OpenAISettings = Field(default_factory=OpenAISettings)
    lm_studio: LMStudioSettings = Field(default_factory=LMStudioSettings)
    ollama: OllamaSettings = Field(default_factory=OllamaSettings)
    llamacpp: LlamaCppSettings = Field(default_factory=LlamaCppSettings)
    mlxlm: MlxLmSettings = Field(default_factory=MlxLmSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    qdrant: QdrantSettings = Field(default_factory=QdrantSettings)
    jwt: JWTSettings = Field(default_factory=JWTSettings)
    memory: MemorySettings = Field(default_factory=MemorySettings)
    tool: ToolSettings = Field(default_factory=ToolSettings)
    pipeline: PipelineSettings = Field(default_factory=PipelineSettings)
    rate_limit: RateLimitSettings = Field(default_factory=RateLimitSettings)
    metrics: MetricsSettings = Field(default_factory=MetricsSettings)
    sentry: SentrySettings = Field(default_factory=SentrySettings)

    # Security
    bcrypt_rounds: int = Field(default=12, ge=4, le=31, description="Bcrypt hashing rounds")

    # Testing settings
    test_database_url: Optional[str] = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/mai_framework_test",
        description="Test database URL",
    )
    test_redis_url: Optional[str] = Field(
        default="redis://localhost:6379/1", description="Test Redis URL"
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        allowed = {"TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in allowed:
            raise ValueError(f"Log level must be one of {allowed}")
        return v_upper

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment."""
        allowed = {"development", "staging", "production", "test"}
        v_lower = v.lower()
        if v_lower not in allowed:
            raise ValueError(f"Environment must be one of {allowed}")
        return v_lower


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create the global settings instance.

    Returns:
        The global Settings instance.
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """Reload settings from environment/config files.

    Useful for testing or when configuration changes.

    Returns:
        The newly loaded Settings instance.
    """
    global _settings
    _settings = Settings()
    return _settings
