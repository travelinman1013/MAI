"""FastAPI authentication middleware and dependencies.

This module provides:
- JWT authentication middleware for FastAPI
- Dependency functions for protecting endpoints
- User injection into request state
- Public endpoint bypass
- Token extraction from Authorization header
"""

from typing import Annotated, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.utils.auth import verify_token, TokenPayload
from src.core.utils.exceptions import AuthenticationError, AuthorizationError
from src.core.utils.logging import get_logger_with_context
from src.infrastructure.database.models import User
from src.infrastructure.database.session import get_db

logger = get_logger_with_context()


# ===== Token Extraction =====


class OptionalHTTPBearer(HTTPBearer):
    """HTTPBearer that doesn't raise on missing credentials.

    This allows endpoints to optionally check for authentication.
    """

    async def __call__(self, request: Request) -> Optional[HTTPAuthorizationCredentials]:
        try:
            return await super().__call__(request)
        except HTTPException:
            return None


# Token extraction schemes
bearer_scheme = HTTPBearer(
    scheme_name="Bearer", description="JWT Bearer token authentication"
)
optional_bearer_scheme = OptionalHTTPBearer(
    scheme_name="OptionalBearer", description="Optional JWT Bearer token authentication"
)


# ===== Token Verification Dependencies =====


async def get_token_payload(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)]
) -> TokenPayload:
    """Extract and verify JWT token from Authorization header.

    This dependency extracts the Bearer token from the Authorization header
    and verifies its signature and expiration.

    Args:
        credentials: HTTP Authorization credentials from header

    Returns:
        Verified token payload

    Raises:
        HTTPException: 401 if token is missing or invalid

    Example:
        ```python
        @app.get("/protected")
        async def protected_endpoint(
            payload: TokenPayload = Depends(get_token_payload)
        ):
            user_id = payload.user_id
            return {"user_id": user_id}
        ```
    """
    token = credentials.credentials

    try:
        payload = verify_token(token, token_type="access")
        logger.debug("Token verified", subject=payload.sub)
        return payload

    except AuthenticationError as e:
        logger.warning("Token verification failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_optional_token_payload(
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials], Depends(optional_bearer_scheme)
    ]
) -> Optional[TokenPayload]:
    """Extract and verify JWT token if present.

    This dependency is for endpoints that optionally support authentication.
    If no token is provided, returns None instead of raising an error.

    Args:
        credentials: HTTP Authorization credentials from header (optional)

    Returns:
        Verified token payload or None if no token provided

    Example:
        ```python
        @app.get("/optional-auth")
        async def optional_auth_endpoint(
            payload: Optional[TokenPayload] = Depends(get_optional_token_payload)
        ):
            if payload:
                return {"authenticated": True, "user_id": payload.user_id}
            return {"authenticated": False}
        ```
    """
    if credentials is None:
        return None

    token = credentials.credentials

    try:
        payload = verify_token(token, token_type="access")
        logger.debug("Optional token verified", subject=payload.sub)
        return payload

    except AuthenticationError as e:
        logger.warning("Optional token verification failed", error=str(e))
        # For optional auth, return None instead of raising
        return None


# ===== User Retrieval Dependencies =====


async def get_current_user(
    payload: Annotated[TokenPayload, Depends(get_token_payload)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Get current authenticated user from database.

    This dependency verifies the token and fetches the user from the database.

    Args:
        payload: Verified token payload
        db: Database session

    Returns:
        User model instance

    Raises:
        HTTPException: 401 if user not found or inactive

    Example:
        ```python
        @app.get("/me")
        async def get_me(
            current_user: User = Depends(get_current_user)
        ):
            return {
                "id": current_user.id,
                "username": current_user.username,
                "email": current_user.email
            }
        ```
    """
    # Get user ID from payload
    user_id_str = payload.user_id or payload.sub

    try:
        user_id = UUID(user_id_str)
    except (ValueError, AttributeError):
        logger.error("Invalid user ID in token", user_id=user_id_str)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Fetch user from database
    user = await db.get(User, user_id)

    if user is None:
        logger.warning("User not found", user_id=str(user_id))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.deleted_at is not None:
        logger.warning("Deleted user attempted access", user_id=str(user_id))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account has been deleted",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.debug("Current user retrieved", user_id=str(user_id), username=user.username)
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """Get current authenticated and active user.

    This dependency adds an additional check to ensure the user is active.

    Args:
        current_user: Current authenticated user

    Returns:
        Active user model instance

    Raises:
        HTTPException: 403 if user is inactive

    Example:
        ```python
        @app.post("/actions")
        async def perform_action(
            current_user: User = Depends(get_current_active_user)
        ):
            # Only active users can perform actions
            return {"status": "success"}
        ```
    """
    if not current_user.is_active:
        logger.warning("Inactive user attempted access", user_id=str(current_user.id))
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive"
        )

    return current_user


async def get_current_superuser(
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> User:
    """Get current authenticated superuser.

    This dependency ensures only superusers can access the endpoint.

    Args:
        current_user: Current authenticated active user

    Returns:
        Superuser model instance

    Raises:
        HTTPException: 403 if user is not a superuser

    Example:
        ```python
        @app.delete("/admin/users/{user_id}")
        async def delete_user(
            user_id: UUID,
            current_user: User = Depends(get_current_superuser)
        ):
            # Only superusers can delete users
            return {"status": "deleted"}
        ```
    """
    if not current_user.is_superuser:
        logger.warning(
            "Non-superuser attempted superuser action", user_id=str(current_user.id)
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have sufficient privileges",
        )

    return current_user


async def get_optional_user(
    payload: Annotated[Optional[TokenPayload], Depends(get_optional_token_payload)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Optional[User]:
    """Get current user if authenticated, None otherwise.

    This dependency is for endpoints that optionally support authentication.

    Args:
        payload: Optional verified token payload
        db: Database session

    Returns:
        User model instance or None

    Example:
        ```python
        @app.get("/content")
        async def get_content(
            current_user: Optional[User] = Depends(get_optional_user)
        ):
            if current_user:
                # Return personalized content
                return {"content": "personalized", "user": current_user.username}
            # Return public content
            return {"content": "public"}
        ```
    """
    if payload is None:
        return None

    # Get user ID from payload
    user_id_str = payload.user_id or payload.sub

    try:
        user_id = UUID(user_id_str)
    except (ValueError, AttributeError):
        logger.warning("Invalid user ID in optional token", user_id=user_id_str)
        return None

    # Fetch user from database
    user = await db.get(User, user_id)

    if user is None or user.deleted_at is not None or not user.is_active:
        return None

    logger.debug("Optional user retrieved", user_id=str(user_id), username=user.username)
    return user


# ===== Type Annotations for Dependencies =====

# These can be used as type hints to make code cleaner
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentActiveUser = Annotated[User, Depends(get_current_active_user)]
CurrentSuperuser = Annotated[User, Depends(get_current_superuser)]
OptionalUser = Annotated[Optional[User], Depends(get_optional_user)]
TokenPayloadDep = Annotated[TokenPayload, Depends(get_token_payload)]
