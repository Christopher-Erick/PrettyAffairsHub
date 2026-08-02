from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone


def send_contact_reply(contact_message, reply_body, *, staff_user=None):
    """Email the customer a reply and mark the contact message handled."""
    reply_body = (reply_body or "").strip()
    if not reply_body:
        raise ValueError("Reply cannot be empty.")

    topic = (contact_message.subject or "").strip() or "your message"
    mail_subject = f"Re: {topic}"
    body = (
        f"Hi {contact_message.name},\n\n"
        f"{reply_body}\n\n"
        f"—\n{settings.SITE_NAME}\n"
    )
    send_mail(
        mail_subject,
        body,
        settings.DEFAULT_FROM_EMAIL,
        [contact_message.email],
        fail_silently=False,
    )

    contact_message.reply_body = reply_body
    contact_message.replied_at = timezone.now()
    contact_message.replied_by = staff_user if getattr(staff_user, "is_authenticated", False) else None
    contact_message.is_handled = True
    contact_message.save(
        update_fields=["reply_body", "replied_at", "replied_by", "is_handled"]
    )
    return contact_message
