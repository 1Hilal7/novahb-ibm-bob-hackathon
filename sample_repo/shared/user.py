"""
Shared User model.

Baseline: email is required (non-nullable str).
This file is depended upon by auth, billing, and notifications modules.
"""
from dataclasses import dataclass


@dataclass
class User:
    id: int
    name: str
    email: str  # required — must always be present

    def display_name(self) -> str:
        return f"{self.name} <{self.email}>"

    def is_contactable(self) -> bool:
        """Return True if the user can be contacted via email."""
        return bool(self.email)
