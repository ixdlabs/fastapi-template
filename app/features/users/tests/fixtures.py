import factory
from app.features.users.models import User, UserType


class UserFactory(factory.Factory):
    class Meta:
        model = User

    username = factory.Faker("user_name")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    type = UserType.CUSTOMER
    email = factory.Faker("email")
    email_verified = True
    joined_at = factory.Faker("date_time_this_decade")

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        raw_password = kwargs.get("raw", "testpassword")
        assert isinstance(self, User), "sanity check failed"
        self.set_password(raw_password)
