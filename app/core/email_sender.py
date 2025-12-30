import abc
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
from pathlib import Path
import smtplib
from typing import Annotated, Literal, override

from fastapi import Depends
from jinja2 import Environment, FileSystemLoader, Template
from pydantic import BaseModel, EmailStr

from app.core.settings import SettingsDep
from fast_depends import Depends as WorkerDepends
from mjml import mjml2html

logger = logging.getLogger(__name__)
base_email_template_path = Path(__file__).parent / "emails"

# Basic Email Structure
# ----------------------------------------------------------------------------------------------------------------------


class Email(BaseModel):
    sender: EmailStr
    receivers: list[EmailStr]
    subject: str
    body_html_template: Path
    body_text_template: Path
    template_data: dict[str, str] | None = None
    attachments: dict[str, bytes] | None = None


# Email Sender Implementations
# The rendering uses Jinja2 templates for flexibility and MJML for HTML email design.
# ----------------------------------------------------------------------------------------------------------------------


class EmailSender(abc.ABC):
    def __init__(self, settings: SettingsDep):
        super().__init__()
        self.settings = settings

    @abc.abstractmethod
    async def send_email(self, email: Email) -> str:
        """Sends an email and returns the email provider's message ID."""
        raise NotImplementedError()

    def render(self, type: Literal["text", "html"], template: Path, data: dict[str, str] | None) -> str:
        """Renders an email template of the given type ('text' or 'html') using Jinja2 and MJML."""
        env = Environment(loader=FileSystemLoader([base_email_template_path, template.parent]))
        jinja_template: Template = env.get_template(template.name)
        content = jinja_template.render(data or {})
        if type == "html":
            try:
                return mjml2html(content)
            except Exception:
                logger.error(f"Failed to compile MJML to HTML: \n{content}", exc_info=True)

        return content


# A simple local email sender that logs emails instead of sending them
# ----------------------------------------------------------------------------------------------------------------------


class LocalEmailSender(EmailSender):
    @override
    async def send_email(self, email: Email) -> str:
        body_html = self.render("html", email.body_html_template, email.template_data)
        body_text = self.render("text", email.body_text_template, email.template_data)
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
        body_html = self.render("html", email.body_html_template, email.template_data)
        body_text = self.render("text", email.body_text_template, email.template_data)

        message = MIMEMultipart("alternative")
        message["Subject"] = email.subject
        message["From"] = email.sender
        message["To"] = ", ".join(email.receivers)
        message.attach(MIMEText(body_text, "plain"))
        message.attach(MIMEText(body_html, "html"))
        if email.attachments:
            for filename, filedata in email.attachments.items():
                part = MIMEText(base64.b64encode(filedata).decode(), "base64")
                part.add_header(
                    "Content-Disposition",
                    f'attachment; filename="{filename}"',
                )
                message.attach(part)

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
EmailSenderWorkerDep = Annotated[EmailSender, WorkerDepends(get_email_sender)]
