"""Tests for the Life Time Fitness data models."""
from __future__ import annotations

from custom_components.lifetime_fitness.model import LifetimeAuthentication


class TestLifetimeAuthentication:
    """Tests for the LifetimeAuthentication class."""

    def test_empty_init(self) -> None:
        """Test empty initialization."""
        auth = LifetimeAuthentication()
        assert auth.access_token is None
        assert auth.sso_id is None
        assert auth.party_id is None
        assert auth.message is None
        assert auth.status is None

    def test_update_non_empty_initial(self) -> None:
        """Test update_non_empty on empty object."""
        auth = LifetimeAuthentication()
        auth.update_non_empty({
            "token": "test_token",
            "ssoId": "test_sso",
            "partyId": "test_party",
            "message": "Success",
            "status": "0",
        })

        assert auth.access_token == "test_token"
        assert auth.sso_id == "test_sso"
        assert auth.party_id == "test_party"
        assert auth.message == "Success"
        assert auth.status == "0"

    def test_update_non_empty_preserves_existing(self) -> None:
        """Test update_non_empty preserves existing values when new value is empty."""
        auth = LifetimeAuthentication()
        auth.update_non_empty({
            "token": "original_token",
            "ssoId": "original_sso",
            "message": "Success",
        })

        # Update with some empty values
        auth.update_non_empty({
            "token": "",  # Empty - should not overwrite
            "ssoId": "new_sso",  # Non-empty - should overwrite
            "message": None,  # None/empty - should not overwrite
        })

        assert auth.access_token == "original_token"  # Preserved
        assert auth.sso_id == "new_sso"  # Updated
        assert auth.message == "Success"  # Preserved

    def test_update_non_empty_adds_new_fields(self) -> None:
        """Test update_non_empty adds new non-empty fields."""
        auth = LifetimeAuthentication()
        auth.update_non_empty({"token": "test_token"})

        auth.update_non_empty({
            "ssoId": "new_sso",
            "partyId": "new_party",
        })

        assert auth.access_token == "test_token"
        assert auth.sso_id == "new_sso"
        assert auth.party_id == "new_party"

    def test_property_accessors(self) -> None:
        """Test all property accessors work correctly."""
        auth = LifetimeAuthentication()
        auth.update_non_empty({
            "token": "access_token_value",
            "ssoId": "sso_id_value",
            "partyId": "party_id_value",
            "message": "message_value",
            "status": "status_value",
        })

        assert auth.access_token == "access_token_value"
        assert auth.sso_id == "sso_id_value"
        assert auth.party_id == "party_id_value"
        assert auth.message == "message_value"
        assert auth.status == "status_value"

    def test_dict_like_access(self) -> None:
        """Test dict-like access still works (UserDict inheritance)."""
        auth = LifetimeAuthentication()
        auth["custom_key"] = "custom_value"

        assert auth["custom_key"] == "custom_value"
        assert auth.get("custom_key") == "custom_value"
        assert auth.get("missing_key") is None
        assert auth.get("missing_key", "default") == "default"
