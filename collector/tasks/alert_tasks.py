"""
Tasks Celery para detección de cambios de posición y envío de alertas.
"""

import logging
import smtplib
from datetime import date, timedelta
from email.mime.text import MIMEText
from typing import Optional

import requests
from sqlalchemy import select

from collector.celery_app import celery_app
from config.settings import settings
from core.database import SessionLocal
from core.models import Alert, AlertEvent, ProjectKeyword, Ranking

logger = logging.getLogger(__name__)


@celery_app.task(name="collector.tasks.alert_tasks.run_all_alerts")
def run_all_alerts():
    """Comprueba todas las alertas activas y dispara notificaciones si aplica."""
    db = SessionLocal()
    try:
        alerts = db.scalars(select(Alert).where(Alert.is_active == True)).all()
        logger.info("Alertas: comprobando %d reglas", len(alerts))
        triggered = 0
        for alert in alerts:
            try:
                if _check_and_fire(db, alert):
                    triggered += 1
            except Exception as exc:
                logger.error(
                    "Alerta id=%d: error al comprobar: %s", alert.id, exc, exc_info=True
                )
        logger.info("Alertas: %d disparadas de %d revisadas", triggered, len(alerts))
    finally:
        db.close()


def _check_and_fire(db, alert: Alert) -> bool:
    """
    Evalúa una alerta. Si se cumple la condición, registra AlertEvent y notifica.
    Retorna True si se disparó.
    """
    pk = db.get(ProjectKeyword, alert.project_keyword_id)
    if not pk or not pk.is_active:
        return False

    today = date.today()
    yesterday = today - timedelta(days=1)

    current = _get_position(db, pk.id, today)
    previous = _get_position(db, pk.id, yesterday)

    if current is None and previous is None:
        return False

    fired, message = _evaluate(alert, current, previous)
    if not fired:
        return False

    event = AlertEvent(
        alert_id=alert.id,
        triggered_at=date.today(),
        previous_position=previous,
        current_position=current,
        message=message,
        sent=False,
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    try:
        _send_notification(alert, event)
        event.sent = True
        db.commit()
    except Exception as exc:
        logger.error("Alerta id=%d: error al enviar notificación: %s", alert.id, exc)

    return True


def _get_position(db, pk_id: int, check_date: date) -> Optional[int]:
    ranking = db.scalar(
        select(Ranking)
        .where(
            Ranking.project_keyword_id == pk_id,
            Ranking.check_date == check_date,
        )
        .order_by(Ranking.check_date.desc())
        .limit(1)
    )
    return ranking.position if ranking else None


def _evaluate(alert: Alert, current: Optional[int], previous: Optional[int]) -> tuple[bool, str]:
    """Evalúa si se cumple la condición de la alerta. Retorna (fired, message)."""
    t = alert.alert_type
    threshold = alert.threshold_positions or 5

    if t == "position_drop":
        if current and previous and current > previous + threshold:
            return True, f"Caída de posición: {previous} → {current} (umbral {threshold})"

    elif t == "position_gain":
        if current and previous and current < previous - threshold:
            return True, f"Subida de posición: {previous} → {current} (umbral {threshold})"

    elif t == "entered_top10":
        if current and current <= 10 and (previous is None or previous > 10):
            return True, f"Entró en Top 10: posición actual {current}"

    elif t == "left_top10":
        if previous and previous <= 10 and (current is None or current > 10):
            return True, f"Salió del Top 10: posición actual {current}"

    elif t == "entered_top3":
        if current and current <= 3 and (previous is None or previous > 3):
            return True, f"Entró en Top 3: posición actual {current}"

    elif t == "not_found":
        if current is None:
            return True, "Keyword no encontrada en los resultados"

    return False, ""


def _send_notification(alert: Alert, event: AlertEvent):
    """Enruta la notificación al canal configurado."""
    channel = alert.channel
    config = alert.channel_config or {}

    if channel == "email":
        _send_email(config, event)
    elif channel == "webhook":
        _send_webhook(config, event)
    elif channel == "slack":
        _send_slack(config, event)
    else:
        logger.warning("Canal desconocido: %s", channel)


def _send_email(config: dict, event: AlertEvent):
    recipient = config.get("email")
    if not recipient:
        raise ValueError("channel_config.email es obligatorio para canal email")

    msg = MIMEText(event.message or "Alerta de ranking disparada")
    msg["Subject"] = f"[RankTracker] Alerta — {event.message[:60]}"
    msg["From"] = settings.alert_from_email
    msg["To"] = recipient

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.sendmail(settings.alert_from_email, [recipient], msg.as_string())

    logger.info("Email enviado a %s: %s", recipient, event.message)


def _send_webhook(config: dict, event: AlertEvent):
    url = config.get("url")
    if not url:
        raise ValueError("channel_config.url es obligatorio para canal webhook")

    payload = {
        "alert_id": event.alert_id,
        "message": event.message,
        "previous_position": event.previous_position,
        "current_position": event.current_position,
        "triggered_at": event.triggered_at.isoformat() if event.triggered_at else None,
    }
    response = requests.post(url, json=payload, timeout=10)
    response.raise_for_status()
    logger.info("Webhook enviado a %s", url)


def _send_slack(config: dict, event: AlertEvent):
    webhook_url = config.get("webhook_url")
    if not webhook_url:
        raise ValueError("channel_config.webhook_url es obligatorio para canal slack")

    payload = {
        "text": f":warning: *RankTracker Alerta*\n{event.message}\n"
                f"Posición anterior: {event.previous_position} → actual: {event.current_position}"
    }
    response = requests.post(webhook_url, json=payload, timeout=10)
    response.raise_for_status()
    logger.info("Slack notificación enviada")
