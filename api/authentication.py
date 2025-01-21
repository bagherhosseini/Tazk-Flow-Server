# authentication.py
from rest_framework import authentication
from rest_framework.exceptions import AuthenticationFailed
import os
from django.contrib.auth.models import AnonymousUser
from clerk_backend_api import Clerk
from clerk_backend_api.jwks_helpers import AuthenticateRequestOptions

class ClerkUser:
    def __init__(self, user_id):
        self.id = user_id
        self.is_authenticated = True
        
    @property
    def is_active(self):
        return True

class ClerkAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return None

        try:
            auth_type, token = auth_header.split()
            if auth_type.lower() != 'bearer':
                return None
        except ValueError:
            return None

        try:
            clerk = Clerk(os.getenv('CLERK_SECRET_KEY'))

            request_state = clerk.authenticate_request(
                request,
                AuthenticateRequestOptions()
            )

            if not request_state or not request_state.payload:
                raise AuthenticationFailed('Invalid token')

            user_id = request_state.payload.get('sub')
            if not user_id:
                raise AuthenticationFailed('No user ID in token')

            return (ClerkUser(user_id), None)

        except Exception as e:
            print(f"Authentication error: {str(e)}")
            raise AuthenticationFailed(f'Authentication failed: {str(e)}')

    def authenticate_header(self, request):
        return 'Bearer realm="api"'