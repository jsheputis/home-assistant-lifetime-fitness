"""Data models for the Life Time Fitness integration."""
from __future__ import annotations

from collections import UserDict
from typing import Any


class LifetimeAuthentication(UserDict[str, Any]):
    """Life Time Fitness authentication data container."""

    def update_non_empty(self, data: dict[str, Any]) -> None:
        """Update this object with non-empty data from `data`.

        On first call, all fields are stored. On subsequent calls,
        only non-empty values are updated to preserve existing data.
        """
        if not self.data:
            super().update(data)
        else:
            filtered = {k: v for (k, v) in data.items() if v}
            super().update(filtered)

    @property
    def access_token(self) -> str | None:
        """Return the access token."""
        return self.get("token")

    @property
    def sso_id(self) -> str | None:
        """Return the SSO ID."""
        return self.get("ssoId")

    @property
    def party_id(self) -> str | None:
        """Return the party ID."""
        return self.get("partyId")

    @property
    def message(self) -> str | None:
        """Return the response message."""
        return self.get("message")

    @property
    def status(self) -> str | None:
        """Return the response status."""
        return self.get("status")
