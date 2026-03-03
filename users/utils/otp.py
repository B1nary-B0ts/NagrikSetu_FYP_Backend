import random
from django.core.cache import cache
from django.conf import settings

OTP_PREFIX = "otp"

def generate_otp():
    return str(random.randint(100000, 999999))

def otp_cache_key(email):
    return f"{OTP_PREFIX}:{email}"

def store_otp(email, otp):
    cache.set(
        otp_cache_key(email),
        otp,
        timeout=settings.OTP_TTL_SECONDS
    )

def verify_otp(email, otp):
    key = otp_cache_key(email)
    stored = cache.get(key)

    if stored is None:
        return False

    if stored != otp:
        return False

    cache.delete(key)
    return True
