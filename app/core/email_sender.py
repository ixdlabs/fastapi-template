import abc
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import smtplib
from typing import Annotated, override

from fastapi import Depends
from jinja2 import Template
from pydantic import BaseModel, EmailStr

from app.core.settings import SettingsDep

logger = logging.getLogger(__name__)


# Basic Email Structure
# ----------------------------------------------------------------------------------------------------------------------


class Email(BaseModel):
    sender: EmailStr
    receivers: list[EmailStr]
    subject: str
    body_html_template: str
    body_text_template: str
    template_data: dict[str, str] | None = None
    attachments: dict[str, bytes] | None = None


# Email Sender Implementations
# The rendering uses Jinja2 templates for flexibility
# ----------------------------------------------------------------------------------------------------------------------


class EmailSender(abc.ABC):
    def __init__(self, settings: SettingsDep):
        super().__init__()
        self.settings = settings

    @abc.abstractmethod
    async def send_email(self, email: Email) -> str:
        """Sends an email and returns the email provider's message ID."""
        raise NotImplementedError()

    def render(self, template: str, data: dict[str, str] | None) -> str:
        jinja_template: Template = Template(template)
        return jinja_template.render(data or {})


# A simple local email sender that logs emails instead of sending them
# ----------------------------------------------------------------------------------------------------------------------


class LocalEmailSender(EmailSender):
    @override
    async def send_email(self, email: Email) -> str:
        body_html = self.render(email.body_html_template, email.template_data)
        body_text = self.render(email.body_text_template, email.template_data)
        logger.info(f"Simulated sending email to {email.receivers}")
        logger.debug(f"Email Subject: {email.subject}")
        logger.debug(f"Email Body (Text): {body_text}")
        logger.debug(f"Email Body (HTML): {body_html}")
        return "local-message-id-placeholder"


# An SMTP email sender that sends emails via an SMTP server
# ----------------------------------------------------------------------------------------------------------------------


class SmtpEmailSender(EmailSender):
    @override
    async def send_email(self, email: Email) -> str:
        body_html = self.render(email.body_html_template, email.template_data)
        body_text = self.render(email.body_text_template, email.template_data)
        message = MIMEMultipart("alternative")
        message["Subject"] = email.subject
        message["From"] = email.sender
        message["To"] = ", ".join(email.receivers)
        message.attach(MIMEText(body_text, "plain"))
        message.attach(MIMEText(body_html, "html"))

        try:
            if self.settings.email_smtp_use_ssl:
                server = smtplib.SMTP_SSL(self.settings.email_smtp_host, self.settings.email_smtp_port)
            else:
                server = smtplib.SMTP(self.settings.email_smtp_host, self.settings.email_smtp_port)
                if self.settings.email_smtp_use_tls:
                    _ = server.starttls()
            if self.settings.email_smtp_username and self.settings.email_smtp_password:
                _ = server.login(self.settings.email_smtp_username, self.settings.email_smtp_password)
            _ = server.send_message(message)
            _ = server.quit()
            logger.info(f"Sent email to {email.receivers} via SMTP")
            return "smtp-message-id-placeholder"
        except Exception as e:
            logger.error(f"Failed to send email via SMTP: {e}")
            raise


# Dependency Injection for EmailSender
# ----------------------------------------------------------------------------------------------------------------------


def get_email_sender(settings: SettingsDep) -> EmailSender:
    if settings.email_sender_type == "local":
        return LocalEmailSender(settings)
    elif settings.email_sender_type == "smtp":
        return SmtpEmailSender(settings)
    raise NotImplementedError(f"Email sender type '{settings.email_sender_type}' is not implemented.")


EmailSenderDep = Annotated[EmailSender, Depends(get_email_sender)]
