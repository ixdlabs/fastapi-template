import factory
from app.features.users.models import User, UserEmailVerification, UserEmailVerificationState, UserType


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


class UserEmailVerificationFactory(factory.Factory):
    class Meta:
        model = UserEmailVerification

    state = UserEmailVerificationState.PENDING
    email = factory.Faker("email")
    expires_at = factory.Faker("future_datetime")

    @factory.post_generation
    def token(self, create, extracted, **kwargs):
        raw_token = kwargs.get("raw", "verificationtoken")
        assert isinstance(self, UserEmailVerification), "sanity check failed"
        self.set_verification_token(raw_token)
