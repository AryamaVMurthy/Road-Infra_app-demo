from fastapi import HTTPException
from datetime import datetime, timedelta
from typing import Dict, Tuple

from app.core.config import settings
from app.core.time import utc_now

# In-memory storage for rate limiting (email -> (count, reset_time))
otp_rate_limit: Dict[str, Tuple[int, datetime]] = {}


def check_otp_rate_limit(email: str):
    if settings.DEV_MODE:
        return

    now = utc_now()
    if email in otp_rate_limit:
        count, reset_time = otp_rate_limit[email]
        if now < reset_time:
            if count >= 3:  # Max 3 attempts per window
                raise HTTPException(
                    status_code=429,
                    detail="Too many OTP requests. Please wait 10 minutes.",
                )
            otp_rate_limit[email] = (count + 1, reset_time)
        else:
            otp_rate_limit[email] = (1, now + timedelta(minutes=10))
    else:
        otp_rate_limit[email] = (1, now + timedelta(minutes=10))
