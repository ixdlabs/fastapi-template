import pytest
# from pathlib import Path

from app.core.email_sender import LocalEmailSender, SmtpEmailSender, get_email_sender
from app.core.settings import SettingsDep


class TestEmailSender:
    def test_get_email_sender_returns_local_sender(self, settings_fixture: SettingsDep):
        settings_fixture.email_sender_type = "local"
        sender = get_email_sender(settings_fixture)
        assert isinstance(sender, LocalEmailSender)
        assert sender.settings == settings_fixture

    def test_get_email_sender_returns_smtp_sender(self, settings_fixture: SettingsDep):
        settings_fixture.email_sender_type = "smtp"
        sender = get_email_sender(settings_fixture)
        assert isinstance(sender, SmtpEmailSender)
        assert sender.settings == settings_fixture

    def test_get_email_sender_raises_not_implemented_error(self, settings_fixture: SettingsDep):
        settings_fixture.email_sender_type = "invalid"  # type: ignore
        with pytest.raises(NotImplementedError, match="Email sender type 'invalid' is not implemented."):
            _ = get_email_sender(settings_fixture)
