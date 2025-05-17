from collections import UserDict

from .const import (
    AuthenticationResults,
)

import logging

_LOGGER = logging.getLogger(__name__)

class LifetimeAuthentication(UserDict):
    """Lifetime Fitness Authentication Data."""
    
    def update_non_empty(self, data) -> None:
        """Update this object with non-empty data from `data`."""
        if not self.data:
            # Start out with all fields
            super().update(data)
        else:
            filtered = {k: v for (k, v) in data.items() if v}
            super().update(filtered)
            
    @property
    def access_token(self) -> str:
        """Access token"""
        return self.get("token")
    
    @property
    def sso_id(self) -> str:
        """SSO ID"""
        return self.get("ssoId")
    
    @property
    def party_id(self) -> str:
        """Party ID"""
        return self.get("partyId")
    
    @property
    def message(self) -> str:
        """Message"""
        return self.get("message")
    
    @property
    def status(self) -> str:
        """Status"""
        return self.get("status")
    
    