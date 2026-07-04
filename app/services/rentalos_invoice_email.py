import logging
from email.message import EmailMessage
from html import escape
from pathlib import Path
from typing import Iterable

from fastapi import BackgroundTasks

from app.config import settings
from app.db.models import RentalBooking, RentalPayment
from app.utils.email import send_email_background


logger = logging.getLogger(__name__)
WORDMARK_CID = "gopanda-wordmark"
WORDMARK_PATH = Path(__file__).resolve().parents[1] / "assets" / "gopanda-wordmark-green-black.png"


def _money(amount: int | None) -> str:
    return f"Rs. {int(amount or 0):,}"


def _format_dt(value) -> str:
    if not value:
        return "-"
    return value.strftime("%d %b %Y, %I:%M %p")


def _customer_name(booking: RentalBooking) -> str:
    customer = booking.customer
    if not customer:
        return "Customer"
    name = f"{customer.firstname or ''} {customer.lastname or ''}".strip()
    return name or "Customer"


def _payment_label(payment_type: str) -> str:
    return payment_type.replace("_", " ").title()


def _payment_rows(booking: RentalBooking, payments: Iterable[RentalPayment]) -> list[tuple[str, str, str, int]]:
    rows: list[tuple[str, str, str, int]] = []
    advance_paid_rows_total = 0

    for payment in payments:
        if payment.payment_type == "advance" and payment.status == "paid":
            advance_paid_rows_total += payment.amount or 0
        signed_amount = -(payment.amount or 0) if payment.payment_type == "refund" else (payment.amount or 0)
        rows.append(
            (
                _payment_label(payment.payment_type),
                payment.status.title(),
                payment.method or "-",
                signed_amount,
            )
        )

    initial_advance = max((booking.advance_paid or 0) - advance_paid_rows_total, 0)
    if initial_advance:
        rows.insert(0, ("Advance At Booking", "Paid", "-", initial_advance))

    return rows


def _total_collected(rows: list[tuple[str, str, str, int]]) -> int:
    total = 0
    for _label, status, _method, amount in rows:
        if status.lower() in {"paid", "refunded"}:
            total += amount
    return total


def _wordmark_header_html(title: str) -> str:
    if WORDMARK_PATH.exists():
        brand = (
            f'<img src="cid:{WORDMARK_CID}" alt="GoPanda" width="190" '
            'style="display:block;width:190px;max-width:70%;height:auto;margin:0 0 12px 0;" />'
        )
    else:
        brand = '<h2 style="margin:0;color:#15803d;">GoPanda</h2>'

    return f"""
          <div style="margin-bottom:20px;">
            {brand}
            <p style="margin:0;color:#6b7280;font-size:20px;">{escape(title)}</p>
          </div>
    """


def _attach_wordmark(msg: EmailMessage) -> None:
    if not WORDMARK_PATH.exists() or not msg.is_multipart():
        return

    payload = msg.get_payload()
    if not payload:
        return

    html_part = payload[-1]
    html_part.add_related(
        WORDMARK_PATH.read_bytes(),
        maintype="image",
        subtype="png",
        cid=f"<{WORDMARK_CID}>",
        filename="gopanda-wordmark.png",
        disposition="inline",
    )


def build_rentalos_invoice_email(
    booking: RentalBooking,
    payments: list[RentalPayment],
    invoice_type: str,
) -> EmailMessage | None:
    customer = booking.customer
    recipient = (customer.email or "").strip() if customer and customer.email else ""
    if not recipient:
        return None

    shop = booking.shop
    bike = booking.bike
    customer_name = _customer_name(booking)
    payment_rows = _payment_rows(booking, payments)
    collected = _total_collected(payment_rows)
    is_final = invoice_type == "final"
    title = "Final Trip Invoice" if is_final else "Booking Invoice"
    subject = f"GoPanda RentalOS {title} - Booking #{booking.id}"

    sender = settings.smtp_sender or settings.smtp_user or "noreply@gopanda.in"
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient

    payment_lines_text = "\n".join(
        f"- {label}: {_money(amount)} ({status}, {method})"
        for label, status, method, amount in payment_rows
    ) or "- No payment rows recorded yet."

    completed_line = f"\nCompleted: {_format_dt(booking.completed_at)}" if is_final else ""
    plain = (
        f"{title}\n\n"
        f"Hello {customer_name},\n\n"
        f"Booking #{booking.id}\n"
        f"Shop: {shop.name if shop else '-'}\n"
        f"Vehicle: {bike.name if bike else '-'} {bike.model if bike else ''}\n"
        f"Pickup: {_format_dt(booking.start_time)}\n"
        f"Return: {_format_dt(booking.end_time)}"
        f"{completed_line}\n\n"
        f"Total: {_money(booking.total_amount)}\n"
        f"Advance paid: {_money(booking.advance_paid)}\n"
        f"Balance due: {_money(booking.balance_due)}\n"
        f"Security deposit: {_money(booking.security_deposit)}\n"
        f"Total collected: {_money(collected)}\n\n"
        f"Payments:\n{payment_lines_text}\n"
    )
    msg.set_content(plain)

    rows_html = "".join(
        "<tr>"
        f"<td style='padding:8px;border-bottom:1px solid #e5e7eb;'>{escape(label)}</td>"
        f"<td style='padding:8px;border-bottom:1px solid #e5e7eb;'>{escape(status)}</td>"
        f"<td style='padding:8px;border-bottom:1px solid #e5e7eb;'>{escape(method)}</td>"
        f"<td style='padding:8px;border-bottom:1px solid #e5e7eb;text-align:right;'>{escape(_money(amount))}</td>"
        "</tr>"
        for label, status, method, amount in payment_rows
    )
    if not rows_html:
        rows_html = "<tr><td colspan='4' style='padding:8px;color:#6b7280;'>No payment rows recorded yet.</td></tr>"

    html = f"""
    <html>
      <body style="font-family:Arial,sans-serif;background:#f3f4f6;padding:24px;color:#111827;">
        <div style="max-width:640px;margin:0 auto;background:#ffffff;border-radius:10px;padding:24px;border:1px solid #e5e7eb;">
          {_wordmark_header_html(title)}
          <p>Hello {escape(customer_name)},</p>
          <p>Here is your invoice for RentalOS booking <strong>#{booking.id}</strong>.</p>
          <div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:8px;padding:16px;margin:18px 0;">
            <p><strong>Shop:</strong> {escape(shop.name if shop else "-")}</p>
            <p><strong>Vehicle:</strong> {escape((bike.name if bike else "-") + (" " + bike.model if bike else ""))}</p>
            <p><strong>Pickup:</strong> {_format_dt(booking.start_time)}</p>
            <p><strong>Return:</strong> {_format_dt(booking.end_time)}</p>
            {f"<p><strong>Completed:</strong> {_format_dt(booking.completed_at)}</p>" if is_final else ""}
          </div>
          <table style="width:100%;border-collapse:collapse;margin-bottom:18px;">
            <tr><td>Total</td><td style="text-align:right;font-weight:bold;">{_money(booking.total_amount)}</td></tr>
            <tr><td>Advance paid</td><td style="text-align:right;">{_money(booking.advance_paid)}</td></tr>
            <tr><td>Balance due</td><td style="text-align:right;">{_money(booking.balance_due)}</td></tr>
            <tr><td>Security deposit</td><td style="text-align:right;">{_money(booking.security_deposit)}</td></tr>
            <tr><td style="padding-top:8px;font-weight:bold;">Total collected</td><td style="text-align:right;padding-top:8px;font-weight:bold;">{_money(collected)}</td></tr>
          </table>
          <h3 style="font-size:16px;margin-bottom:8px;">Payment ledger</h3>
          <table style="width:100%;border-collapse:collapse;border:1px solid #e5e7eb;">
            <thead>
              <tr style="background:#f9fafb;">
                <th style="padding:8px;text-align:left;">Type</th>
                <th style="padding:8px;text-align:left;">Status</th>
                <th style="padding:8px;text-align:left;">Method</th>
                <th style="padding:8px;text-align:right;">Amount</th>
              </tr>
            </thead>
            <tbody>{rows_html}</tbody>
          </table>
        </div>
      </body>
    </html>
    """
    msg.add_alternative(html, subtype="html")
    _attach_wordmark(msg)
    return msg


def enqueue_rentalos_invoice_email(
    background_tasks: BackgroundTasks,
    booking: RentalBooking,
    payments: list[RentalPayment],
    invoice_type: str,
) -> bool:
    smtp_host = settings.smtp_host
    smtp_port = settings.smtp_port
    smtp_user = settings.smtp_user
    smtp_password = settings.smtp_password
    if not smtp_host or not smtp_user or not smtp_password:
        logger.info("RentalOS invoice email skipped because SMTP is not configured")
        return False

    msg = build_rentalos_invoice_email(booking, payments, invoice_type)
    if not msg:
        logger.info("RentalOS invoice email skipped because customer email is missing")
        return False

    background_tasks.add_task(
        send_email_background,
        smtp_host,
        smtp_port,
        smtp_user,
        smtp_password,
        msg,
    )
    return True
