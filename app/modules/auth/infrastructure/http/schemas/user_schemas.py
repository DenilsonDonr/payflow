import uuid

from pydantic import BaseModel


class RegisterUserRequest(BaseModel):
    # Plain strings on purpose: `Email` and `Password` validate them, and a Pydantic validator here
    # would answer 422 naming the failing field, which the router deliberately does not reveal.
    email: str
    password: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    role_id: int
