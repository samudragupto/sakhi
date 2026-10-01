"""Security headers and input sanitization middleware."""

import re
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Remove control characters except newline and tab
CONTROL_CHAR_REGEX = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def sanitize_text(text: str, max_length: int = 500) -> str:
    """Sanitize user text input by stripping control chars and truncating."""
    if not text:
        return ""
    cleaned = CONTROL_CHAR_REGEX.sub("", text)
    return cleaned.strip()[:max_length]


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware enforcing production security headers and strict CSP."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Attach security headers to all responses."""
        response: Response = await call_next(request)

        # Content Security Policy (strict, self-contained, no external CDNs)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self'; "
            "img-src 'self' data: blob:; "
            "media-src 'self' blob: data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "object-src 'none'; "
            "base-uri 'self';"
        )

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "microphone=(self), geolocation=(self), camera=(self)"
        )
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response
