from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from .config import Settings, get_settings

bearer = HTTPBearer(auto_error=False)


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    if not settings.clerk_jwks_url or not settings.clerk_issuer:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Clerk is not configured")

    try:
        key = PyJWKClient(settings.clerk_jwks_url).get_signing_key_from_jwt(credentials.credentials).key
        options = {"verify_aud": bool(settings.clerk_audience)}
        claims = jwt.decode(
            credentials.credentials,
            key,
            algorithms=["RS256"],
            issuer=settings.clerk_issuer,
            audience=settings.clerk_audience if settings.clerk_audience else None,
            options=options,
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token") from exc

    subject = claims.get("sub")
    if not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has no subject")
    return claims
