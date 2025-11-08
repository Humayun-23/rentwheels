# Password Reset Feature

## Overview
The password reset feature allows users to reset their password using a secure token-based system.

## API Endpoints

### 1. Request Password Reset
**Endpoint:** `POST /api/v1/password-reset/request`

**Request Body:**
```json
{
  "email": "user@example.com"
}
```

**Response:**
```json
{
  "message": "Password reset token generated. Token: <token> (Valid for 1 hour. In production, this would be sent via email.)"
}
```

**Notes:**
- For security, the endpoint always returns a success message, even if the email doesn't exist
- The token is valid for 1 hour
- Any previous unused tokens for the same user are automatically invalidated
- **Development only:** The token is returned in the response. In production, this should be sent via email

### 2. Confirm Password Reset
**Endpoint:** `POST /api/v1/password-reset/confirm`

**Request Body:**
```json
{
  "token": "<reset_token>",
  "new_password": "newSecurePassword123"
}
```

**Response:**
```json
{
  "message": "Password has been successfully reset. You can now login with your new password."
}
```

**Validation:**
- `new_password` must be at least 8 characters long
- `new_password` must be at most 128 characters long
- Token must be valid and not expired
- Token must not have been used already

## Usage Flow

### Example 1: Using cURL

```bash
# Step 1: Request password reset
curl -X POST http://localhost:8000/api/v1/password-reset/request \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com"}'

# Response will include the token (in development)
# {
#   "message": "Password reset token generated. Token: abc123xyz... (Valid for 1 hour. In production, this would be sent via email.)"
# }

# Step 2: Reset password with token
curl -X POST http://localhost:8000/api/v1/password-reset/confirm \
  -H "Content-Type: application/json" \
  -d '{
    "token": "abc123xyz...",
    "new_password": "myNewPassword123"
  }'

# Response:
# {
#   "message": "Password has been successfully reset. You can now login with your new password."
# }
```

### Example 2: Using Python requests

```python
import requests

# Step 1: Request password reset
response = requests.post(
    "http://localhost:8000/api/v1/password-reset/request",
    json={"email": "user@example.com"}
)
print(response.json())
# Extract token from message (in development)

# Step 2: Reset password
token = "abc123xyz..."  # Extract from above response
response = requests.post(
    "http://localhost:8000/api/v1/password-reset/confirm",
    json={
        "token": token,
        "new_password": "myNewPassword123"
    }
)
print(response.json())
```

## Security Features

1. **Token Expiration:** Tokens expire after 1 hour
2. **One-time Use:** Tokens can only be used once
3. **Token Invalidation:** Previous unused tokens are invalidated when a new reset is requested
4. **Email Privacy:** The API doesn't reveal whether an email exists in the system
5. **Secure Token Generation:** Uses cryptographically secure random tokens (32 bytes, URL-safe)
6. **Password Hashing:** New passwords are hashed using bcrypt before storage

## Production Considerations

### Email Integration
In production, you should integrate an email service to send reset links. Recommended services:
- SendGrid
- AWS SES
- Mailgun
- Postmark

Example integration point in `passwordreset.py`:
```python
# After creating reset_token
from app.utils.email import send_password_reset_email

reset_link = f"https://yourdomain.com/reset-password?token={token}"
send_password_reset_email(
    to_email=user.email,
    reset_link=reset_link
)
```

### Rate Limiting
Consider adding rate limiting to prevent abuse:
```python
@limiter.limit("3/hour")  # Max 3 requests per hour per IP
@router.post("/request", response_model=PasswordResetResponse)
def request_password_reset(...):
    ...
```

### Environment Variables
Add these to your `.env` file:
```
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USERNAME=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
EMAIL_FROM=noreply@rentwheels.com
RESET_TOKEN_EXPIRY_HOURS=1
```

## Database Schema

The `password_reset_tokens` table:
```sql
CREATE TABLE password_reset_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    is_used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Error Handling

| Status Code | Error | Description |
|-------------|-------|-------------|
| 200 | Success | Password reset successful |
| 400 | Invalid token | Token is invalid, expired, or already used |
| 404 | User not found | User associated with token doesn't exist |
| 422 | Validation error | Invalid request body (e.g., password too short) |

## Testing

Test the password reset flow:
```bash
# Create a test user first (if not exists)
curl -X POST http://localhost:8000/api/v1/users \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "oldPassword123",
    "phone_number": "1234567890",
    "user_type": "customer"
  }'

# Request password reset
curl -X POST http://localhost:8000/api/v1/password-reset/request \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'

# Use the token from response to reset password
curl -X POST http://localhost:8000/api/v1/password-reset/confirm \
  -H "Content-Type: application/json" \
  -d '{
    "token": "<token_from_previous_response>",
    "new_password": "newPassword123"
  }'

# Try logging in with new password
curl -X POST http://localhost:8000/api/v1/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d 'username=test@example.com&password=newPassword123'
```
