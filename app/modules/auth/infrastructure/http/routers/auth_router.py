from fastapi import APIRouter, Depends, HTTPException

from app.modules.auth.application.use_cases.register_user_use_case import RegisterUserUseCase
from app.modules.auth.domain.exceptions.user_already_exists import UserAlreadyExistsError
from app.modules.auth.infrastructure.http.schemas.user_schemas import (
    RegisterUserRequest,
    UserResponse,
)
from app.modules.auth.infrastructure.persistence.repository.postgres_user_repository import (
    PostgresUserRepository,
)
from app.modules.auth.infrastructure.security.argon2_password_hasher import Argon2PasswordHasher
from app.shared.persistence.postgres_connection import ConnectionDB

# One answer for a malformed email, a password of the wrong length and a taken email, so the
# response does not tell a caller whether an address is registered.
INVALID_CREDENTIALS = "Invalid email or password."


def get_register_user_use_case() -> RegisterUserUseCase:
    repository = PostgresUserRepository(connection=ConnectionDB())
    return RegisterUserUseCase(
        user_repository_port=repository,
        password_hasher_port=Argon2PasswordHasher(),
    )

router_auth = APIRouter()

@router_auth.post(
    "/auth/register",
    summary="Register a new user",
    status_code=201,
    response_model=UserResponse,
)
async def register_user(
    request: RegisterUserRequest,
    use_case: RegisterUserUseCase = Depends(get_register_user_use_case),
):
    try:
        user = await use_case.execute(email=request.email, password=request.password)
    except (ValueError, TypeError, UserAlreadyExistsError) as e:
        raise HTTPException(status_code=400, detail=INVALID_CREDENTIALS) from e
    # Built field by field so the password hash can never leak into the response.
    return UserResponse(id=user.id, email=user.email.value, role_id=user.role_id)
