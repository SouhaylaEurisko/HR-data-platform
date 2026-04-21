"""
Authentication-related dependency providers.
"""
from fastapi import HTTPException, Request, status


def get_request_user_id(request: Request) -> int:
    """
    Extract and validate user ID from gateway header.
    """
    user_id_header = request.headers.get("x-user-id")
    if not user_id_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-User-Id header",
        )

    try:
        return int(user_id_header)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid X-User-Id header",
        )
