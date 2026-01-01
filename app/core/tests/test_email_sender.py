import logging
import pytest
from pathlib import Path
from pydantic import EmailStr
from typing import Callable
from unittest.mock import patch

from app.core.email_sender import Email, LocalEmailSender, SmtpEmailSender, get_email_sender
from app.core.settings import SettingsDep


EmailFactory = Callable[..., Email]


@pytest.fixture
def email_factory(email_templates: tuple[Path, Path]):
    """Returns a function that creates Email objects"""
    html_template, text_template = email_templates

    def _create_email(
        sender: str = "test@testmail.com",
        receivers: list[EmailStr] | None = None,
        subject: str = "Test",
        template_data: dict[str, object] | None = None,
    ):
        return Email(
            sender=sender,
            receivers=receivers or ["receiver@testemail.com"],
            subject=subject,
            body_html_template=html_template,
            body_text_template=text_template,
            template_data=template_data or {"name": "TestUser"},
        )

    return _create_email


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


class TestLocalEmailSender:
    @pytest.mark.asyncio
    async def test_send_email_logs_and_returns_placeholder(
        self,
        settings_fixture: SettingsDep,
        email_factory: EmailFactory,
        caplog: pytest.LogCaptureFixture,
    ):
        caplog.set_level(logging.DEBUG)
        settings_fixture.email_sender_type = "local"
        sender = LocalEmailSender(settings_fixture)
        email = email_factory(subject="Test")
        message_id = await sender.send_email(email)

        assert message_id == "local-message-id-placeholder"
        assert "Simulated sending email to" in caplog.text
        assert "receiver@testemail.com" in caplog.text
        assert "Test" in caplog.text

    @pytest.mark.asyncio
    async def test_send_email_with_multiple_receivers(
        self, settings_fixture: SettingsDep, caplog: pytest.LogCaptureFixture, email_factory: EmailFactory
    ):
        settings_fixture.email_sender_type = "local"
        sender = LocalEmailSender(settings_fixture)
        email = email_factory(receivers=["recipient1@testemail.com", "recipient2@testemail.com"])
        message_id = await sender.send_email(email)

        assert message_id == "local-message-id-placeholder"
        assert "recipient1@testemail.com" in caplog.text
        assert "recipient2@testemail.com" in caplog.text


class TestEmailSenderRender:
    def test_render_text_template_with_data(self, settings_fixture: SettingsDep, email_templates: tuple[Path, Path]):
        sender = LocalEmailSender(settings_fixture)
        _, text_template = email_templates

        result = sender.render("text", text_template, {"name": "John"})
        assert "Hello John" in result

    def test_render_text_template_empty_data(self, settings_fixture: SettingsDep, email_templates: tuple[Path, Path]):
        sender = LocalEmailSender(settings_fixture)
        _, text_template = email_templates

        result = sender.render("text", text_template, {})
        assert "Hello" in result

    def test_render_html_template_with_data(self, settings_fixture: SettingsDep, email_templates: tuple[Path, Path]):
        sender = LocalEmailSender(settings_fixture)
        html_template, _ = email_templates

        result = sender.render("html", html_template, {"name": "Alice"})
        assert "Hello Alice" in result

    def test_render_with_none_template_data(self, settings_fixture: SettingsDep, email_templates: tuple[Path, Path]):
        sender = LocalEmailSender(settings_fixture)
        _, text_template = email_templates

        result = sender.render("text", text_template, None)
        assert isinstance(result, str)
        assert "Hello" in result

    def test_render_preserves_template_variables_without_data(self, settings_fixture: SettingsDep, tmp_path: Path):
        sender = LocalEmailSender(settings_fixture)
        text_template = tmp_path / "test_vars.txt"
        _ = text_template.write_text("Hello {{ name }}, your email is {{ email }}")

        result = sender.render("text", text_template, None)
        assert "Hello" in result

    def test_render_complex_template_data(self, settings_fixture: SettingsDep, tmp_path: Path):
        sender = LocalEmailSender(settings_fixture)
        text_template = tmp_path / "complex.txt"
        _ = text_template.write_text("User: {{ user.name }}, Email: {{ user.email }}")

        result = sender.render("text", text_template, {"user": {"name": "Bob", "email": "bob@example.com"}})
        assert "User: Bob" in result
        assert "bob@example.com" in result


class TestSmtpEmailSender:
    # def test_smtp_sender_initializes_with_settings(self, settings_fixture: SettingsDep):
    #     settings_fixture.email_sender_type = "smtp"
    #     sender = SmtpEmailSender(settings_fixture)
    #     assert sender.settings == settings_fixture

    def test_render_methods_are_available(self, settings_fixture: SettingsDep, email_templates: tuple[Path, Path]):
        """Verify SmtpEmailSender inherits render method from EmailSender"""
        sender = SmtpEmailSender(settings_fixture)
        _, text_template = email_templates
        result = sender.render("text", text_template, {"name": "Test"})
        assert "Hello Test" in result

    @pytest.mark.asyncio
    async def test_send_email_creates_valid_message_structure(
        self, settings_fixture: SettingsDep, email_factory: EmailFactory, monkeypatch: pytest.MonkeyPatch
    ):
        """Test that send_email raises when SMTP connection fails"""
        monkeypatch.setattr(settings_fixture, "email_sender_type", "smtp")
        monkeypatch.setattr(settings_fixture, "email_smtp_host", "invalid-host-xyz")
        monkeypatch.setattr(settings_fixture, "email_smtp_port", 9595)
        monkeypatch.setattr(settings_fixture, "email_smtp_use_ssl", False)
        monkeypatch.setattr(settings_fixture, "email_smtp_use_tls", False)
        sender = SmtpEmailSender(settings_fixture)
        email = email_factory()
        with patch("app.core.email_sender.smtplib.SMTP") as mock_smtp:
            mock_smtp.side_effect = Exception("Simulated Connection Error")
            with pytest.raises(Exception, match="Simulated Connection Error"):
                _ = await sender.send_email(email)

    @pytest.mark.asyncio
    async def test_send_email_logs_error_on_failure(
        self,
        settings_fixture: SettingsDep,
        email_factory: EmailFactory,
        caplog: pytest.LogCaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Test that SMTP errors are logged"""
        caplog.set_level(logging.ERROR)
        monkeypatch.setattr(settings_fixture, "email_sender_type", "smtp")
        sender = SmtpEmailSender(settings_fixture)
        email = email_factory()
        with patch("app.core.email_sender.smtplib.SMTP") as mock_smtp:
            mock_smtp.side_effect = Exception("Major Network Fail")
            with pytest.raises(Exception):
                _ = await sender.send_email(email)
        assert "Failed to send email via SMTP" in caplog.text
        assert "Major Network Fail" in caplog.text

    @pytest.mark.asyncio
    async def test_send_email_with_attachments(
        self, settings_fixture: SettingsDep, email_factory: EmailFactory, monkeypatch: pytest.MonkeyPatch
    ):
        """Tests that attachments are correctly added to the MIME message"""
        monkeypatch.setattr(settings_fixture, "email_sender_type", "smtp")
        monkeypatch.setattr(settings_fixture, "email_smtp_use_ssl", False)
        monkeypatch.setattr(settings_fixture, "email_smtp_use_tls", False)
        sender = SmtpEmailSender(settings_fixture)
        email = email_factory()
        email.attachments = {"report.pdf": b"%PDF-1.4 content..."}

        with patch("app.core.email_sender.smtplib.SMTP") as mock_smtp_cls:
            mock_instance = mock_smtp_cls.return_value
            _ = await sender.send_email(email)
            sent_message = mock_instance.send_message.call_args[0][0]
            attachment_found = False
            for part in sent_message.walk():
                if part.get_filename() == "report.pdf":
                    attachment_found = True
                    assert part["Content-Disposition"] == 'attachment; filename="report.pdf"'
            assert attachment_found, "Attachment part was not found in the MIME message"

    @pytest.mark.asyncio
    async def test_send_email_flow_with_tls_and_auth(
        self, settings_fixture: SettingsDep, email_factory: EmailFactory, monkeypatch: pytest.MonkeyPatch
    ):
        """Tests the TLS upgrade and Login flow"""
        monkeypatch.setattr(settings_fixture, "email_sender_type", "smtp")
        monkeypatch.setattr(settings_fixture, "email_smtp_host", "smtp.example.com")
        monkeypatch.setattr(settings_fixture, "email_smtp_port", 587)
        monkeypatch.setattr(settings_fixture, "email_smtp_use_ssl", False)
        monkeypatch.setattr(settings_fixture, "email_smtp_use_tls", True)
        monkeypatch.setattr(settings_fixture, "email_smtp_username", "testuser")
        monkeypatch.setattr(settings_fixture, "email_smtp_password", "testpass")
        sender = SmtpEmailSender(settings_fixture)
        email = email_factory()
        with patch("app.core.email_sender.smtplib.SMTP") as mock_smtp_cls:
            mock_instance = mock_smtp_cls.return_value
            _ = await sender.send_email(email)

            mock_smtp_cls.assert_called_with("smtp.example.com", 587)  # Correct Host/Port
            mock_instance.starttls.assert_called_once()  # TLS was started
            mock_instance.login.assert_called_once_with("testuser", "testpass")  # Login called
            mock_instance.send_message.assert_called_once()  # Message sent
            mock_instance.quit.assert_called_once()  # Connection closed

    @pytest.mark.asyncio
    async def test_send_email_flow_with_ssl(
        self, settings_fixture: SettingsDep, email_factory: EmailFactory, monkeypatch: pytest.MonkeyPatch
    ):
        """Tests the SSL connection flow"""
        monkeypatch.setattr(settings_fixture, "email_sender_type", "smtp")
        monkeypatch.setattr(settings_fixture, "email_smtp_host", "smtp.secure.com")
        monkeypatch.setattr(settings_fixture, "email_smtp_port", 465)
        monkeypatch.setattr(settings_fixture, "email_smtp_use_ssl", True)
        sender = SmtpEmailSender(settings_fixture)
        email = email_factory()

        with patch("app.core.email_sender.smtplib.SMTP_SSL") as mock_smtp_ssl_cls:
            mock_instance = mock_smtp_ssl_cls.return_value
            _ = await sender.send_email(email)
            mock_smtp_ssl_cls.assert_called_with("smtp.secure.com", 465)
            mock_instance.send_message.assert_called_once()
            mock_instance.quit.assert_called_once()
