"""
Chatbot Gateway Router — API gateway that routes requests to the chatbot service.
"""
import httpx
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..config import config, get_db
from ..models.user import UserAccount as User
from ..dependencies.auth import get_current_user

router = APIRouter(prefix="/api", tags=["chatbot"])

# Chatbot service base URL
CHATBOT_SERVICE_URL = config.chatbot_service_url


async def forward_request_to_chatbot(
    method: str,
    path: str,
    request: Request,
    current_user: Optional[User] = None,
) -> Any:
    """
    Forward a request to the chatbot service.
    
    Args:
        method: HTTP method (GET, POST, DELETE, etc.)
        path: Path to forward (e.g., "/api/conversations")
        request: Original FastAPI request
        current_user: Current authenticated user (optional)
        
    Returns:
        Response from chatbot service
    """
    # Build full URL
    url = f"{CHATBOT_SERVICE_URL}{path}"
    
    # Get request body if present
    body = None
    if method in ["POST", "PUT", "PATCH"]:
        try:
            body = await request.json()
        except Exception:
            body = None
    
    # Get query parameters
    query_params = dict(request.query_params)
    
    # Prepare headers (forward relevant headers)
    headers = {}
    if request.headers.get("content-type"):
        headers["content-type"] = request.headers["content-type"]
    if request.headers.get("accept"):
        headers["accept"] = request.headers["accept"]
    # Forward Authorization header if present (for debugging, though chatbot service doesn't need it)
    if request.headers.get("authorization"):
        headers["authorization"] = request.headers["authorization"]
    
    # Add user context if available (for future use)
    if current_user:
        headers["X-User-Id"] = str(current_user.id)
        headers["X-User-Email"] = current_user.email
    
    # Forward request to chatbot service
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        try:
            response = await client.request(
                method=method,
                url=url,
                json=body,
                params=query_params,
                headers=headers,
            )
            
            # If response is successful, return it
            if response.status_code < 400:
                # Handle 204 No Content (DELETE requests) - no response body
                if response.status_code == 204:
                    return None
                # Try to parse JSON, but handle empty responses
                try:
                    return response.json() if response.content else None
                except Exception:
                    # If JSON parsing fails, return text or None
                    return response.text if response.text else None
            else:
                # Forward error response with proper status code
                try:
                    error_detail = response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
                except Exception:
                    error_detail = response.text or "Chatbot service error"
                
                raise HTTPException(
                    status_code=response.status_code,
                    detail=error_detail if isinstance(error_detail, str) else error_detail.get("detail", "Chatbot service error")
                )
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Chatbot service timeout"
            )
        except httpx.ConnectError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Chatbot service unavailable"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error forwarding request to chatbot service: {str(e)}"
            )


# ──────────────────────────────────────────────
# Conversation Endpoints (Gateway)
# ──────────────────────────────────────────────

@router.get("/conversations")
async def list_conversations_gateway(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """
    List all conversations (gateway to chatbot service).
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"List conversations request from user {current_user.id} ({current_user.email})")
    return await forward_request_to_chatbot("GET", "/api/conversations", request, current_user)


@router.get("/conversations/{conversation_id}")
async def get_conversation_gateway(
    conversation_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """
    Get a conversation by ID (gateway to chatbot service).
    """
    return await forward_request_to_chatbot(
        "GET",
        f"/api/conversations/{conversation_id}",
        request,
        current_user
    )


@router.post("/conversations/send")
async def send_message_gateway(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """
    Send a message to a conversation (gateway to chatbot service).
    """
    return await forward_request_to_chatbot(
        "POST",
        "/api/conversations/send",
        request,
        current_user
    )


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation_gateway(
    conversation_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """
    Delete a conversation (gateway to chatbot service).
    """
    await forward_request_to_chatbot(
        "DELETE",
        f"/api/conversations/{conversation_id}",
        request,
        current_user
    )
    # Return 204 No Content (no response body)
    return None


# ──────────────────────────────────────────────
# Legacy Chat Endpoint (Gateway)
# ──────────────────────────────────────────────

@router.post("/chat")
async def chat_gateway(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """
    Legacy chat endpoint (gateway to chatbot service).
    This endpoint can be used for backward compatibility.
    """
    # For legacy endpoint, we might need to transform the request
    # For now, forward as-is to chatbot service
    return await forward_request_to_chatbot("POST", "/api/chat", request, current_user)
