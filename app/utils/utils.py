from passlib.context import CryptContext
import hashlib

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash a password with bcrypt (handles passwords > 72 chars)"""
    # Bcrypt has a 72-byte limit. For longer passwords, hash with SHA256 first
    if len(password.encode('utf-8')) > 72:
        password = hashlib.sha256(password.encode()).hexdigest()
    
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hash"""
    # If original password was > 72 bytes, it was hashed with SHA256 first
    if len(plain_password.encode('utf-8')) > 72:
        plain_password = hashlib.sha256(plain_password.encode()).hexdigest()
    
    return pwd_context.verify(plain_password, hashed_password)
