"""Test naming conventions and serialization for DTOs."""

import json
import pytest
from datetime import datetime
from pydantic import ValidationError
from common.use_cases.user.commands import CreateUserCommand, UpdateUserCommand
from common.use_cases.user.queries import UserResponse, ListUsersQuery, SearchUsersQuery


class TestNamingConventions:
    """Test snake_case to camelCase conversion."""

    def test_command_snake_case_to_camel_case(self):
        """Test CreateUserCommand converts snake_case to camelCase in JSON."""
        # Create command with snake_case fields (Python)
        command = CreateUserCommand(
            first_name="Jane",
            last_name="Doe",
            email_address="jane.doe@example.com",
            phone_number="+1234567890"
        )
        
        # Serialize to JSON with aliases (camelCase)
        json_data = command.model_dump(by_alias=True)
        
        # Assert JSON uses camelCase
        assert "firstName" in json_data
        assert "lastName" in json_data
        assert "emailAddress" in json_data
        assert "phoneNumber" in json_data
        
        # Assert snake_case keys are NOT in JSON
        assert "first_name" not in json_data
        assert "last_name" not in json_data
        assert "email_address" not in json_data
        assert "phone_number" not in json_data
        
        # Verify values
        assert json_data["firstName"] == "Jane"
        assert json_data["lastName"] == "Doe"
        assert json_data["emailAddress"] == "jane.doe@example.com"

    def test_response_snake_case_to_camel_case(self):
        """Test UserResponse converts snake_case to camelCase in JSON."""
        # Create response with snake_case fields
        response = UserResponse(
            user_id="user-123",
            first_name="Jane",
            last_name="Doe",
            email_address="jane@example.com",
            phone_number="+1234567890",
            account_status="active",
            created_at=datetime(2025, 1, 13, 10, 0, 0),
            updated_at=datetime(2025, 1, 13, 10, 0, 0)
        )
        
        # Serialize to JSON with aliases
        json_data = response.model_dump(by_alias=True)
        
        # Assert JSON uses camelCase
        assert "userId" in json_data
        assert "firstName" in json_data
        assert "lastName" in json_data
        assert "emailAddress" in json_data
        assert "phoneNumber" in json_data
        assert "accountStatus" in json_data
        assert "createdAt" in json_data
        assert "updatedAt" in json_data
        assert "lastLoginAt" in json_data

    def test_query_snake_case_to_camel_case(self):
        """Test SearchUsersQuery converts snake_case to camelCase."""
        query = SearchUsersQuery(
            search_term="Jane",
            page=1,
            page_size=20
        )
        
        json_data = query.model_dump(by_alias=True)
        
        assert "searchTerm" in json_data
        assert "pageSize" in json_data
        assert "search_term" not in json_data
        assert "page_size" not in json_data


class TestDeserialization:
    """Test camelCase JSON to snake_case Python."""

    def test_command_camel_case_to_snake_case(self):
        """Test CreateUserCommand accepts camelCase JSON."""
        json_str = '''
        {
            "firstName": "John",
            "lastName": "Smith",
            "emailAddress": "john.smith@example.com",
            "phoneNumber": "+1234567890"
        }
        '''
        
        # Parse from camelCase JSON
        command = CreateUserCommand.model_validate_json(json_str)
        
        # Assert Python uses snake_case
        assert command.first_name == "John"
        assert command.last_name == "Smith"
        assert command.email_address == "john.smith@example.com"
        assert command.phone_number == "+1234567890"

    def test_response_camel_case_to_snake_case(self):
        """Test UserResponse accepts camelCase JSON."""
        json_str = '''
        {
            "userId": "user-456",
            "firstName": "John",
            "lastName": "Smith",
            "emailAddress": "john@example.com",
            "phoneNumber": "+1234567890",
            "accountStatus": "active",
            "createdAt": "2025-01-13T10:00:00",
            "updatedAt": "2025-01-13T10:00:00",
            "lastLoginAt": null
        }
        '''
        
        response = UserResponse.model_validate_json(json_str)
        
        # Assert Python uses snake_case
        assert response.user_id == "user-456"
        assert response.first_name == "John"
        assert response.last_name == "Smith"
        assert response.email_address == "john@example.com"
        assert response.account_status == "active"

    def test_accepts_both_naming_conventions(self):
        """Test populate_by_name allows both snake_case and camelCase."""
        # camelCase input
        camel_data = {
            "firstName": "Jane",
            "lastName": "Doe",
            "emailAddress": "jane@example.com"
        }
        command1 = CreateUserCommand.model_validate(camel_data)
        
        # snake_case input
        snake_data = {
            "first_name": "Jane",
            "last_name": "Doe",
            "email_address": "jane@example.com"
        }
        command2 = CreateUserCommand.model_validate(snake_data)
        
        # Both should work and produce same result
        assert command1.first_name == command2.first_name
        assert command1.last_name == command2.last_name
        assert command1.email_address == command2.email_address


class TestValidation:
    """Test field validations."""

    def test_name_validation_rejects_numbers(self):
        """Test names with numbers are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            CreateUserCommand(
                first_name="Jane123",
                last_name="Doe",
                email_address="jane@example.com"
            )
        
        assert "Names can only contain letters" in str(exc_info.value)

    def test_name_validation_accepts_hyphens(self):
        """Test names with hyphens are accepted."""
        command = CreateUserCommand(
            first_name="Mary-Jane",
            last_name="O'Brien",
            email_address="mary@example.com"
        )
        assert command.first_name == "Mary-Jane"

    def test_email_validation(self):
        """Test invalid email is rejected."""
        with pytest.raises(ValidationError):
            CreateUserCommand(
                first_name="Jane",
                last_name="Doe",
                email_address="invalid-email"
            )

    def test_phone_validation(self):
        """Test phone number pattern validation."""
        # Valid formats
        command1 = CreateUserCommand(
            first_name="Jane",
            last_name="Doe",
            email_address="jane@example.com",
            phone_number="+1234567890"
        )
        assert command1.phone_number == "+1234567890"
        
        # Invalid format
        with pytest.raises(ValidationError):
            CreateUserCommand(
                first_name="Jane",
                last_name="Doe",
                email_address="jane@example.com",
                phone_number="123-456-7890"  # Not E.164 format
            )

    def test_extra_fields_forbidden(self):
        """Test extra fields are rejected (extra='forbid')."""
        with pytest.raises(ValidationError) as exc_info:
            CreateUserCommand.model_validate({
                "firstName": "Jane",
                "lastName": "Doe",
                "emailAddress": "jane@example.com",
                "extraField": "not allowed"
            })
        
        assert "Extra inputs are not permitted" in str(exc_info.value)


class TestRoundTrip:
    """Test serialization and deserialization round trips."""

    def test_command_round_trip(self):
        """Test command can be serialized and deserialized."""
        # Create original
        original = CreateUserCommand(
            first_name="Jane",
            last_name="Doe",
            email_address="jane@example.com",
            phone_number="+1234567890"
        )
        
        # Serialize to JSON (camelCase)
        json_str = original.model_dump_json(by_alias=True)
        json_data = json.loads(json_str)
        assert "firstName" in json_data
        
        # Deserialize back
        restored = CreateUserCommand.model_validate_json(json_str)
        
        # Should be equal
        assert restored.first_name == original.first_name
        assert restored.last_name == original.last_name
        assert restored.email_address == original.email_address
        assert restored.phone_number == original.phone_number

    def test_response_round_trip_with_datetime(self):
        """Test response with datetime serializes correctly."""
        # Create original
        now = datetime(2025, 1, 13, 10, 30, 45)
        original = UserResponse(
            user_id="user-123",
            first_name="Jane",
            last_name="Doe",
            email_address="jane@example.com",
            account_status="active",
            created_at=now,
            updated_at=now
        )
        
        # Serialize to JSON (camelCase)
        json_str = original.model_dump_json(by_alias=True)
        json_data = json.loads(json_str)
        
        # Check datetime is ISO formatted
        assert json_data["createdAt"] == "2025-01-13T10:30:45"
        assert json_data["updatedAt"] == "2025-01-13T10:30:45"
        
        # Deserialize back
        restored = UserResponse.model_validate_json(json_str)
        
        # Datetimes should be equal
        assert restored.created_at == original.created_at
        assert restored.updated_at == original.updated_at


class TestUpdateCommand:
    """Test partial update command."""

    def test_partial_update_single_field(self):
        """Test updating only one field."""
        command = UpdateUserCommand(first_name="Jane")
        
        json_data = command.model_dump(by_alias=True, exclude_unset=True)
        
        # Only firstName should be present
        assert "firstName" in json_data
        assert "lastName" not in json_data
        assert "emailAddress" not in json_data
        assert json_data["firstName"] == "Jane"

    def test_partial_update_multiple_fields(self):
        """Test updating multiple fields."""
        command = UpdateUserCommand(
            first_name="Jane",
            email_address="jane.new@example.com"
        )
        
        json_data = command.model_dump(by_alias=True, exclude_unset=True)
        
        assert "firstName" in json_data
        assert "emailAddress" in json_data
        assert "lastName" not in json_data


class TestPaginationResponse:
    """Test pagination response structure."""

    def test_pagination_metadata(self):
        """Test pagination metadata uses camelCase."""
        users = [
            UserResponse(
                user_id=f"user-{i}",
                first_name=f"User",
                last_name=f"{i}",
                email_address=f"user{i}@example.com",
                account_status="active",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            for i in range(10)
        ]
        
        from common.use_cases.user.queries import UserListResponse
        
        response = UserListResponse(
            users=users,
            total_count=100,
            page=2,
            page_size=10,
            total_pages=10,
            has_next_page=True,
            has_previous_page=True
        )
        
        json_data = response.model_dump(by_alias=True)
        
        # Check pagination fields are camelCase
        assert "totalCount" in json_data
        assert "pageSize" in json_data
        assert "totalPages" in json_data
        assert "hasNextPage" in json_data
        assert "hasPreviousPage" in json_data
        
        assert json_data["totalCount"] == 100
        assert json_data["hasNextPage"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
