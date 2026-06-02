"""Security utilities for rate limiting and protection."""
import logging
from functools import wraps
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django_ratelimit.decorators import ratelimit
from django.contrib import messages
from rest_framework.permissions import BasePermission
from django.utils import timezone
from accounts.models import APIKey

logger = logging.getLogger(__name__)


def get_client_ip(request):
    """Get the client's IP address from the request, handling reverse proxy."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    
    # Ensure we always return a valid IP string
    return ip or '127.0.0.1'


def custom_ratelimit(rate='5/h', method='POST', block=False, key='ip'):
    """Custom rate limit decorator with better error handling.
    
    Args:
        rate: Rate limit string (e.g., '5/h', '10/m', '100/d')
        method: HTTP methods to limit (e.g., 'POST', 'GET', 'ALL')
        block: Whether to block when limit is exceeded
        key: Key function or string ('ip', 'user', etc.)
    """
    def decorator(func):
        @wraps(func)
        @ratelimit(key=lambda group, request: get_client_ip(request), rate=rate, method=method, block=False)
        def wrapper(request, *args, **kwargs):
            # Check if rate limited
            was_limited = getattr(request, 'limited', False)
            if was_limited:
                ip = get_client_ip(request)
                logger.warning(
                    f"Rate limit exceeded for {func.__name__} from IP {ip}"
                )
                
                # Return appropriate response based on request type
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'error': 'Rate limit exceeded. Please try again later.'
                    }, status=429)
                
                messages.error(
                    request,
                    'Too many requests. Please try again later.'
                )
                return render(
                    request,
                    'accounts/error/rate_limit.html',
                    {'retry_after': 3600},
                    status=429
                )
            
            return func(request, *args, **kwargs)
        return wrapper
    return decorator


class HasValidAPIKey(BasePermission):
    """Permission that checks for a valid API key.

    The key is accepted from, in order of priority:
      - `Authorization: Bearer <key>` header
      - `X-API-Key` header
      - `HTTP_X_API_KEY` (for some proxies)
      - `api_key` query parameter

    Optionally enforces an `allowed_origin` restriction if set on the key.
    """

    message = "Invalid or missing API key."

    def has_permission(self, request, view):  # pragma: no cover - simple glue logic
        auth_header = request.headers.get("Authorization") or request.META.get("HTTP_AUTHORIZATION")
        if auth_header and auth_header.lower().startswith("bearer "):
            raw_key = auth_header[7:].strip()
        else:
            raw_key = (
                request.headers.get("X-API-Key")
                or request.META.get("HTTP_X_API_KEY")
                or request.query_params.get("api_key")
            )
        if not raw_key:
            return False

        api_key = APIKey.objects.filter(key=raw_key, is_active=True).first()
        if not api_key:
            return False

        origin = request.headers.get("Origin") or request.META.get("HTTP_ORIGIN")
        if api_key.allowed_origin and origin:
            # Basic prefix check; you can refine to exact match if needed
            if not origin.startswith(api_key.allowed_origin):
                return False

        api_key.last_used_at = timezone.now()
        api_key.save(update_fields=["last_used_at"])

        return True


def log_security_event(event_type, request, details=None, user=None):
    """Log security-related events."""
    ip = get_client_ip(request)
    user_str = str(user) if user else (str(request.user) if request.user.is_authenticated else 'Anonymous')
    user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')[:100]
    
    log_message = (
        f"Security Event: {event_type} | "
        f"User: {user_str} | "
        f"IP: {ip} | "
        f"UA: {user_agent}"
    )
    
    if details:
        log_message += f" | Details: {details}"
    
    logger.warning(log_message)


def check_token_expiry(token_obj, expiry_hours=24):
    """Check if a token has expired."""
    from django.utils import timezone
    from datetime import timedelta
    
    if not hasattr(token_obj, 'created_at'):
        return False
    
    if not token_obj.created_at:
        return True
    
    expiry_time = token_obj.created_at + timedelta(hours=expiry_hours)
    return timezone.now() > expiry_time


def validate_invite_token(token_model, token_value, expiry_hours=72):
    """Validate an invite token."""
    try:
        token_obj = token_model.objects.get(token=token_value)
    except token_model.DoesNotExist:
        return False, None, "Invalid or expired token."
    
    if hasattr(token_obj, 'accepted') and token_obj.accepted:
        return False, token_obj, "This invitation has already been accepted."
    
    if check_token_expiry(token_obj, expiry_hours):
        return False, token_obj, "This invitation has expired."
    
    return True, token_obj, None