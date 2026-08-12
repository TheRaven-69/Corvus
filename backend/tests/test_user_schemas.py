import pytest
from app.schemas.user import UserRegister
from pydantic import ValidationError


def test_user_register_accepts_valid_data() -> None:
    user = UserRegister(
        email="vadim@example.com",
        username="vadim_123",
        first_name="Vadim",
        last_name="Test",
        password="strong=password",
    )

    assert user.email == "vadim@example.com"
    assert user.username == "vadim_123"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("email", "not-an-email"),
        ("username", "ab"),
        ("username", "invalid username"),
        ("first_name", ""),
        ("last_name", ""),
        ("password", "short"),
    ],
)
def test_user_register_rejects_invalid_data(
    field: str,
    value: str,
) -> None:
    data = {
        "email": "vadim@example.com",
        "username": "vadim_123",
        "first_name": "Vadim",
        "last_name": "Test",
        "password": "strong-password",
    }
    data[field] = value

    with pytest.raises(ValidationError):
        UserRegister(**data)
