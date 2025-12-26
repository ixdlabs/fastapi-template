from datetime import timezone
import factory

from app.features.users.models.user_action import UserAction, UserActionType, UserActionState


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
