from datetime import timezone
import factory

from app.features.users.models.user import UserType, User


class UserFactory(factory.Factory[User]):
    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        model = User

    username = factory.Faker("user_name")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    type = UserType.CUSTOMER
    email = factory.Faker("email")
    joined_at = factory.Faker("date_time_this_decade", tzinfo=timezone.utc)
    password_set_at = factory.Faker("past_datetime", tzinfo=timezone.utc)

    @factory.post_generation
    def password(self, create: object, extracted: object, **kwargs: object):
        raw_password = str(kwargs.get("raw", "testpassword"))
        assert isinstance(self, User), "sanity check failed"
        self.set_password(raw_password)
