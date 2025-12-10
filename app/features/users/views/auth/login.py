import uuid
from fastapi import APIRouter
from pydantic import BaseModel


class LoginInput(BaseModel):
    username: str
    password: str


class LoginOutput(BaseModel):
    access_token: str
    refresh_token: str
    user: "LoginOutputUser"


class LoginOutputUser(BaseModel):
    id: uuid.UUID
    username: str
    email: str
    full_name: str | None = None


router = APIRouter()


@router.post("/login")
async def login(input: LoginInput) -> LoginOutput:
    return LoginOutput(
        access_token="dummy_access_token",
        refresh_token="dummy_refresh_token",
        user=LoginOutputUser(id=uuid.uuid4(), username=input.username, email="john@example.com", full_name="John Doe"),
    )
