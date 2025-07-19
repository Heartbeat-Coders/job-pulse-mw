# app/auth/backend.py
from starlette.authentication import (
    AuthenticationBackend, AuthCredentials, SimpleUser
)
from starlette.requests import HTTPConnection

class DummyAuthBackend(AuthenticationBackend):
    async def authenticate(self, conn: HTTPConnection):
        # For now, this just fakes an "authenticated" user
        return AuthCredentials(["authenticated"]), SimpleUser("GuestUser")


guest_user = DummyAuthBackend()