"""ShellUI JWT authentication for the REST API."""

from urllib.parse import urlparse, urlunparse

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientError
from rest_framework import authentication, exceptions

User = get_user_model()

_jwks_client = None


def _shellui_jwks_url():
    """Build JWKS URL, using IPv4 loopback to avoid macOS localhost → ::1 resets."""
    parsed = urlparse(settings.SHELLUI_JWT_ORIGIN.rstrip('/'))
    hostname = parsed.hostname or ''
    if hostname in ('localhost', '::1'):
        netloc = parsed.netloc.replace(hostname, '127.0.0.1', 1)
        parsed = parsed._replace(netloc=netloc)
    origin = urlunparse(parsed).rstrip('/')
    return f'{origin}/.well-known/jwks.json'


def _get_jwks_client():
    global _jwks_client
    if _jwks_client is None and settings.SHELLUI_JWT_ORIGIN:
        _jwks_client = PyJWKClient(
            _shellui_jwks_url(),
            cache_keys=True,
            lifespan=600,
            timeout=10,
        )
    return _jwks_client


class ShellUIJWTAuthentication(authentication.BaseAuthentication):
    """Validate Bearer JWTs issued by the ShellUI identity service."""

    keyword = 'bearer'

    def authenticate(self, request):
        auth_header = authentication.get_authorization_header(request).split()
        if not auth_header or auth_header[0].lower() != self.keyword.encode():
            return None

        if len(auth_header) != 2:
            raise exceptions.AuthenticationFailed('Invalid Authorization header.')

        token = auth_header[1].decode('utf-8')
        payload = self._decode_token(token)
        return self._get_or_create_user(payload), payload

    def _decode_token(self, token):
        if settings.SHELLUI_JWT_SECRET:
            try:
                return jwt.decode(
                    token,
                    settings.SHELLUI_JWT_SECRET,
                    algorithms=[settings.SHELLUI_JWT_ALGORITHM],
                    options={'require': ['exp']},
                )
            except jwt.PyJWTError as exc:
                raise exceptions.AuthenticationFailed('Invalid or expired token.') from exc

        jwks_client = _get_jwks_client()
        if jwks_client is None:
            raise exceptions.AuthenticationFailed('JWT authentication is not configured.')

        try:
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            return jwt.decode(
                token,
                signing_key.key,
                algorithms=settings.SHELLUI_JWT_ALGORITHMS,
                options={'require': ['exp']},
            )
        except (PyJWKClientError, OSError) as exc:
            raise exceptions.AuthenticationFailed(
                'Unable to reach the identity service JWKS endpoint.',
            ) from exc
        except jwt.PyJWTError as exc:
            raise exceptions.AuthenticationFailed('Invalid or expired token.') from exc

    def _get_or_create_user(self, payload):
        email = payload.get('email')
        if not email and isinstance(payload.get('user'), dict):
            email = payload['user'].get('email')
        if not email:
            raise exceptions.AuthenticationFailed('Token missing email claim.')

        user_metadata = payload.get('user_metadata') or {}
        name = user_metadata.get('name') or user_metadata.get('full_name') or ''
        is_staff = user_metadata.get('is_staff') is True

        user, _ = User.objects.get_or_create(
            username=email,
            defaults={'email': email},
        )

        updated_fields = []
        if user.email != email:
            user.email = email
            updated_fields.append('email')

        if name:
            parts = name.split(None, 1)
            first_name = parts[0]
            last_name = parts[1] if len(parts) > 1 else ''
            if user.first_name != first_name:
                user.first_name = first_name
                updated_fields.append('first_name')
            if user.last_name != last_name:
                user.last_name = last_name
                updated_fields.append('last_name')

        if user.is_staff != is_staff:
            user.is_staff = is_staff
            updated_fields.append('is_staff')

        if updated_fields:
            user.save(update_fields=updated_fields)

        return user
