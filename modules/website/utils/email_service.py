import logging
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

logger = logging.getLogger(__name__)


def send_transactional_email(subject, template_name, context, recipient_list, from_email=None):
    """
    Renders an HTML email template and sends it to recipients with plain-text fallback.
    """
    from_email = from_email or settings.DEFAULT_FROM_EMAIL
    if isinstance(recipient_list, str):
        recipient_list = [recipient_list]

    try:
        html_content = render_to_string(template_name, context)
        text_content = strip_tags(html_content)

        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=recipient_list
        )
        msg.attach_alternative(html_content, "text/html")
        sent = msg.send(fail_silently=False)
        return sent > 0
    except Exception as e:
        logger.error(f"Failed to send email to {recipient_list}: {e}")
        return False


def send_status_update_email(user_email, user_name, entity_name, new_status, notes=""):
    """Sends status change notification email."""
    context = {
        'user_name': user_name,
        'entity_name': entity_name,
        'new_status': new_status,
        'notes': notes,
        'platform_name': getattr(settings, 'PLATFORM_NAME', 'ImpactBridge'),
    }
    return send_transactional_email(
        subject=f"Status Update: {entity_name} is now {new_status}",
        template_name='emails/status_update.html',
        context=context,
        recipient_list=[user_email]
    )


def send_welcome_email(user_email, user_name, role_name):
    """Sends new user registration welcome email."""
    context = {
        'user_name': user_name,
        'role_name': role_name,
        'platform_name': getattr(settings, 'PLATFORM_NAME', 'ImpactBridge'),
    }
    return send_transactional_email(
        subject="Welcome to ImpactBridge CSR & Job Intelligence Platform",
        template_name='emails/welcome_email.html',
        context=context,
        recipient_list=[user_email]
    )
