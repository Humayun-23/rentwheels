import os
from email.message import EmailMessage
import smtplib
import logging


logger = logging.getLogger(__name__)

def send_email_background(host: str, port: int, user: str, password: str, msg: EmailMessage):
    """Reusable background task for sending emails"""
    try:
        if port == 465:
            server = smtplib.SMTP_SSL(host, port, timeout=15)
        else:
            server = smtplib.SMTP(host, port, timeout=15)
            server.starttls()

        with server:
            server.login(user, password)
            server.send_message(msg)
        logger.info("Email sent successfully", extra={"recipient": msg.get("To"), "subject": msg.get("Subject")})
    except Exception:
        logger.exception("Failed to send email", extra={"recipient": msg.get("To"), "subject": msg.get("Subject")})

def build_receipt_email(booking, customer, bike, shop) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = f"GoPanda Booking Receipt - #{str(booking.id)[:8]}"
    msg["From"] = os.getenv("SMTP_USER", "noreply@gopanda.com")
    msg["To"] = customer.email
    
    html = f"""
    <html>
        <body style="font-family: sans-serif; background-color: #f3f4f6; padding: 2rem;">
            <div style="max-width: 500px; margin: 0 auto; background: white; padding: 2rem; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                <div style="text-align: center; margin-bottom: 2rem;">
                    <h2 style="color: #22c55e; margin: 0;">GoPanda</h2>
                    <p style="color: #6b7280; font-size: 0.9rem; margin: 0;">Booking Receipt</p>
                </div>
                
                <h3 style="margin-top: 0; color: #1f2937;">Hello {customer.full_name},</h3>
                <p style="color: #4b5563;">Your booking request has been successfully received! The shop owner is currently reviewing it.</p>
                
                <div style="background-color: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 1.5rem; margin: 1.5rem 0;">
                    <h4 style="margin-top: 0; color: #374151; font-size: 1.1rem; border-bottom: 1px solid #e5e7eb; padding-bottom: 0.5rem;">Booking #{str(booking.id)[:8]}</h4>
                    
                    <p style="margin: 0.5rem 0;"><strong>Vehicle:</strong> {bike.name} {bike.model}</p>
                    <p style="margin: 0.5rem 0;"><strong>Pickup:</strong> {booking.start_time.strftime('%b %d, %Y %I:%M %p')}</p>
                    <p style="margin: 0.5rem 0;"><strong>Return:</strong> {booking.end_time.strftime('%b %d, %Y %I:%M %p')}</p>
                    <p style="margin: 0.5rem 0;"><strong>Shop:</strong> {shop.name} ({shop.city})</p>
                    
                    <hr style="border: none; border-top: 1px dashed #e5e7eb; margin: 1rem 0;" />
                    
                    <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                        <span style="color: #6b7280;">Token Paid via UPI:</span>
                        <strong style="color: #22c55e;">₹{booking.token_amount}</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span style="color: #6b7280;">Balance at Shop:</span>
                        <strong style="color: #1f2937;">₹{max(0, booking.total_price - booking.token_amount)}</strong>
                    </div>
                </div>
                
                <p style="color: #6b7280; font-size: 0.85rem; text-align: center;">If your booking is rejected, your token amount will be fully refunded.</p>
            </div>
        </body>
    </html>
    """
    msg.set_content(f"Your booking for {bike.name} is received. Total: ₹{booking.total_price}. Token Paid: ₹{booking.token_amount}.")
    msg.add_alternative(html, subtype="html")
    return msg

def build_cancellation_email(booking, customer, bike) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = f"GoPanda Booking Cancelled - #{str(booking.id)[:8]}"
    msg["From"] = os.getenv("SMTP_USER", "noreply@gopanda.com")
    msg["To"] = customer.email
    
    html = f"""
    <html>
        <body style="font-family: sans-serif; background-color: #f3f4f6; padding: 2rem;">
            <div style="max-width: 500px; margin: 0 auto; background: white; padding: 2rem; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                <div style="text-align: center; margin-bottom: 2rem;">
                    <div style="background-color: #fee2e2; color: #ef4444; width: 48px; height: 48px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 1rem auto; font-size: 1.5rem; font-weight: bold;">!</div>
                    <h2 style="color: #ef4444; margin: 0;">Booking Cancelled</h2>
                </div>
                
                <h3 style="margin-top: 0; color: #1f2937;">Hello {customer.full_name},</h3>
                <p style="color: #4b5563;">Unfortunately, your booking request for <strong>{bike.name} {bike.model}</strong> was rejected or cancelled.</p>
                <p style="color: #4b5563;">If you paid a token advance (₹{booking.token_amount}), it will be automatically refunded to your original payment method within 5-7 business days.</p>
                
                <div style="margin-top: 2rem; text-align: center;">
                    <a href="https://gopanda.com/search-vehicles" style="background-color: #22c55e; color: white; padding: 0.75rem 1.5rem; text-decoration: none; border-radius: 8px; font-weight: bold;">Find Another Vehicle</a>
                </div>
            </div>
        </body>
    </html>
    """
    msg.set_content(f"Your booking for {bike.name} was cancelled. Your token of ₹{booking.token_amount} will be refunded.")
    msg.add_alternative(html, subtype="html")
    return msg
