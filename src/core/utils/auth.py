"""JWT authentication and password hashing utilities.

This module provides secure authentication functionality with:
- JWT token creation and verification using PyJWT
- Password hashing using bcrypt (cost factor 12)
- Token expiration handling
- Secure password verification
- FastAPI integration support
"""

from fastapi import Depends, HTTPException, status
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import bcrypt
import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError

from src.core.utils.config import JWTSettings, get_settings
from src.core.utils.exceptions import (
    AuthenticationError,
    AuthorizationError,
)
from src.core.utils.logging import get_logger_with_context

logger = get_logger_with_context()


class TokenPayload:
    """JWT token payload data structure.

    Attributes:
        sub: Subject (usually user ID or username)
        exp: Expiration timestamp
        iat: Issued at timestamp
        type: Token type (access, refresh)
        user_id: User UUID
        username: Username
        additional: Any additional claims
    """

    def __init__(
        self,
        sub: str,
        exp: datetime,
        iat: datetime,
        type: str = "access",
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        **additional,
    ):
        self.sub = sub
        self.exp = exp
        self.iat = iat
        self.type = type
        self.user_id = user_id
        self.username = username
        self.additional = additional

    def to_dict(self) -> dict[str, Any]:
        """Convert payload to dictionary."""
        data = {
            "sub": self.sub,
            "exp": int(self.exp.timestamp()),
            "iat": int(self.iat.timestamp()),
            "type": self.type,
        }

        if self.user_id:
            data["user_id"] = self.user_id
        if self.username:
            data["username"] = self.username

        data.update(self.additional)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TokenPayload":
        """Create payload from dictionary.

        Args:
            data: Token payload dictionary

        Returns:
            TokenPayload instance
        """
        return cls(
            sub=data["sub"],
            exp=datetime.fromtimestamp(data["exp"], tz=timezone.utc),
            iat=datetime.fromtimestamp(data["iat"], tz=timezone.utc),
            type=data.get("type", "access"),
            user_id=data.get("user_id"),
            username=data.get("username"),
            **{k: v for k, v in data.items() if k not in ["sub", "exp", "iat", "type", "user_id", "username"]},
        )


# ===== Password Hashing =====


def hash_password(password: str, rounds: Optional[int] = None) -> str:
    """Hash password using bcrypt.

    Args:
        password: Plain text password
        rounds: Bcrypt cost factor (default: 12 from settings)

    Returns:
        Hashed password string

    Example:
        ```python
        hashed = hash_password("my_secure_password")
        # Store hashed in database
        ```
    """
    if rounds is None:
        rounds = get_settings().bcrypt_rounds

    # Convert password to bytes and hash
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=rounds)
    hashed = bcrypt.hashpw(password_bytes, salt)

    # Return as string
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password from database

    Returns:
        True if password matches hash

    Example:
        ```python
        is_valid = verify_password(user_input, stored_hash)
        if is_valid:
            # Grant access
        ```
    """
    try:
        password_bytes = plain_password.encode("utf-8")
        hashed_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hashed_bytes)

    except Exception as e:
        logger.error("Password verification failed", error=str(e))
        return False


# ===== JWT Token Management =====


def create_access_token(
    subject: str,
    user_id: Optional[str] = None,
    username: Optional[str] = None,
    expires_delta: Optional[timedelta] = None,
    settings: Optional[JWTSettings] = None,
    **additional_claims,
) -> str:
    """Create JWT access token.

    Args:
        subject: Token subject (usually user ID or username)
        user_id: User UUID (optional)
        username: Username (optional)
        expires_delta: Custom expiration time. If None, uses default from settings.
        settings: JWT settings. If None, uses global settings.
        **additional_claims: Additional claims to include in token

    Returns:
        Encoded JWT token string

    Example:
        ```python
        token = create_access_token(
            subject=str(user.id),
            user_id=str(user.id),
            username=user.username,
            expires_delta=timedelta(hours=1)
        )
        # Return token to client
        ```
    """
    jwt_settings = settings or get_settings().jwt

    # Calculate expiration time
    if expires_delta is not None:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=jwt_settings.access_token_expire_minutes
        )

    # Create payload
    payload = TokenPayload(
        sub=subject,
        exp=expire,
        iat=datetime.now(timezone.utc),
        type="access",
        user_id=user_id,
        username=username,
        **additional_claims,
    )

    # Encode token
    try:
        token = jwt.encode(
            payload.to_dict(), jwt_settings.secret, algorithm=jwt_settings.algorithm
        )
        logger.debug("Access token created", subject=subject, expires=expire.isoformat())
        return token

    except Exception as e:
        logger.error("Failed to create access token", error=str(e))
        raise AuthenticationError(
            "Failed to create access token", user_id=user_id, error=str(e)
        )


def create_refresh_token(
    subject: str,
    user_id: Optional[str] = None,
    username: Optional[str] = None,
    expires_delta: Optional[timedelta] = None,
    settings: Optional[JWTSettings] = None,
) -> str:
    """Create JWT refresh token.

    Args:
        subject: Token subject (usually user ID or username)
        user_id: User UUID (optional)
        username: Username (optional)
        expires_delta: Custom expiration time. If None, uses default from settings.
        settings: JWT settings. If None, uses global settings.

    Returns:
        Encoded JWT refresh token string

    Example:
        ```python
        refresh_token = create_refresh_token(
            subject=str(user.id),
            user_id=str(user.id),
            username=user.username
        )
        # Store refresh token in database
        ```
    """
    jwt_settings = settings or get_settings().jwt

    # Calculate expiration time
    if expires_delta is not None:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=jwt_settings.refresh_token_expire_days
        )

    # Create payload
    payload = TokenPayload(
        sub=subject,
        exp=expire,
        iat=datetime.now(timezone.utc),
        type="refresh",
        user_id=user_id,
        username=username,
    )

    # Encode token
    try:
        token = jwt.encode(
            payload.to_dict(), jwt_settings.secret, algorithm=jwt_settings.algorithm
        )
        logger.debug("Refresh token created", subject=subject, expires=expire.isoformat())
        return token

    except Exception as e:
        logger.error("Failed to create refresh token", error=str(e))
        raise AuthenticationError(
            "Failed to create refresh token", user_id=user_id, error=str(e)
        )


def verify_token(
    token: str, token_type: str = "access", settings: Optional[JWTSettings] = None
) -> TokenPayload:
    """Verify and decode JWT token.

    Args:
        token: Encoded JWT token
        token_type: Expected token type (access or refresh)
        settings: JWT settings. If None, uses global settings.

    Returns:
        Decoded token payload

    Raises:
        AuthenticationError: If token is invalid, expired, or wrong type

    Example:
        ```python
        try:
            payload = verify_token(token_from_header)
            user_id = payload.user_id
        except AuthenticationError:
            # Invalid token
        ```
    """
    jwt_settings = settings or get_settings().jwt

    try:
        # Decode token
        payload_dict = jwt.decode(
            token, jwt_settings.secret, algorithms=[jwt_settings.algorithm]
        )

        # Parse payload
        payload = TokenPayload.from_dict(payload_dict)

        # Verify token type
        if payload.type != token_type:
            raise AuthenticationError(
                f"Invalid token type: expected {token_type}, got {payload.type}",
                expected=token_type,
                actual=payload.type,
            )

        logger.debug("Token verified successfully", type=token_type, subject=payload.sub)
        return payload

    except ExpiredSignatureError:
        logger.warning("Token expired", type=token_type)
        raise AuthenticationError("Token has expired", token_type=token_type, retryable=False)

    except InvalidTokenError as e:
        logger.warning("Invalid token", error=str(e))
        raise AuthenticationError(f"Invalid token: {e}", retryable=False)

    except Exception as e:
        logger.error("Token verification failed", error=str(e))
        raise AuthenticationError(f"Token verification failed: {e}", retryable=False)


def decode_token_without_verification(token: str) -> Optional[TokenPayload]:
    """Decode token without verifying signature (for debugging/inspection only).

    Args:
        token: Encoded JWT token

    Returns:
        Decoded token payload or None if decoding fails

    Warning:
        This does NOT verify the token signature. Only use for debugging or
        inspection purposes. Never use for authentication/authorization.
    """
    try:
        payload_dict = jwt.decode(token, options={"verify_signature": False})
        return TokenPayload.from_dict(payload_dict)

    except Exception as e:
        logger.error("Failed to decode token", error=str(e))
        return None


# ===== Token Utilities =====


def get_token_expiration(token: str) -> Optional[datetime]:
    """Get token expiration time without verification.

    Args:
        token: Encoded JWT token

    Returns:
        Expiration datetime or None if token is invalid
    """
    payload = decode_token_without_verification(token)
    return payload.exp if payload else None


def is_token_expired(token: str) -> bool:
    """Check if token is expired without full verification.

    Args:
        token: Encoded JWT token

    Returns:
        True if token is expired
    """
    exp = get_token_expiration(token)
    if exp is None:
        return True

    return datetime.now(timezone.utc) > exp


def get_current_user() -> str:
    """
    Placeholder function to simulate getting the current authenticated user.
    In a real application, this would involve decoding a JWT,
    checking database, etc.
    """
    # For now, we'll return a hardcoded user.
    # In a real scenario, you'd extract user information from a token
    # or session and handle authentication failures.
    # raise HTTPException(
    #     status_code=status.HTTP_401_UNAUTHORIZED,
    #     detail="Not authenticated"
    # )
    return "test_user"
