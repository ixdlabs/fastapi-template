import factory
from app.core.email_sender import Email


class EmailFactory(factory.Factory[Email]):
    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        model = Email

    sender = "test@testemail.com"
    receivers = ["recipient@testemail.com"]
    subject = "Test"
    template_data = {"name": "TestUser"}
    body_html_template = None
    body_text_template = None
