"""
Auth service module.

Handles user authentication and session management.
Imports User but does not depend on email being non-null
for its core authentication logic.
Hilal is working on profile settings and authentication state flow.
"""
from sample_repo.shared.user import User


def authenticate_user(user_id: int, password_hash: str, db_users: dict) -> User | None:
    """
    Authenticate a user by ID and password hash.
    Returns the User object if authentication succeeds, None otherwise.
    Email is not part of the authentication check.
    """
    user = db_users.get(user_id)
    if user is None:
        return None

    stored_hash = db_users.get(f"{user_id}:hash")
    if stored_hash != password_hash:
        return None

    return user


def create_session(user: User) -> dict:
    """
    Create a session token payload for the authenticated user.
    Does not require or validate user.email.
    """
    return {
        "user_id": user.id,
        "user_name": user.name,
        "session_token": f"tok_{user.id}_placeholder",
    }


def get_profile(user: User) -> dict:
    """
    Return profile data for the user.
    Email is included if present but is not required for the profile to be valid.
    The auth module handles email as optional display data, not an auth invariant.
    """
    profile = {
        "id": user.id,
        "name": user.name,
    }
    # Email shown in profile but auth flow does not break if it is absent
    if user.email:
        profile["email"] = user.email

    return profile


def revoke_session(session_token: str) -> bool:
    """Revoke a user session by token."""
    print(f"[auth] Revoking session {session_token}")
    return True
