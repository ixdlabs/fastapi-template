from datetime import timedelta, timezone, datetime
import jwt
from app.config.settings import Settings
from app.features.users.models import User


def jwt_encode(user: User, settings: Settings) -> str:
    jwt_expiration = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expiration_minutes)
    jwt_payload = {"sub": str(user.id), "exp": jwt_expiration}
    access_token = jwt.encode(payload=jwt_payload, key=settings.jwt_secret_key, algorithm="HS256")
    return access_token
