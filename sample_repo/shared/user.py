"""
Shared User model.

DEMO CHANGE: email is now nullable (str | None).
Previously email was a required str field.
This file is depended upon by auth, billing, and notifications modules.
"""
from dataclasses import dataclass


@dataclass
class User:
    id: int
    name: str
    email: str | None  # nullable — email may not be provided

    def display_name(self) -> str:
        return f"{self.name} <{self.email}>"

    def is_contactable(self) -> bool:
        """Return True if the user can be contacted via email."""
        return bool(self.email)
