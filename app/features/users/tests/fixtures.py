from datetime import timezone
import factory
from app.features.users.models import User, UserAction, UserActionState, UserActionType, UserType


class UserFactory(factory.Factory):
    class Meta:
        model = User

    username = factory.Faker("user_name")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    type = UserType.CUSTOMER
    email = factory.Faker("email")
    joined_at = factory.Faker("date_time_this_decade", tzinfo=timezone.utc)

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        raw_password = kwargs.get("raw", "testpassword")
        assert isinstance(self, User), "sanity check failed"
        self.set_password(raw_password)


class UserActionFactory(factory.Factory):
    class Meta:
        model = UserAction

    type = UserActionType.EMAIL_VERIFICATION
    state = UserActionState.PENDING
    expires_at = factory.Faker("future_datetime", tzinfo=timezone.utc)

    @factory.post_generation
    def token(self, create, extracted, **kwargs):
        raw_token = kwargs.get("raw", "testtoken")
        assert isinstance(self, UserAction), "sanity check failed"
        self.set_token(raw_token)
