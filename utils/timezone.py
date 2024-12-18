
from datetime import datetime
import pytz

def get_user_timezone(user):
    """Get timezone object for user's timezone string"""
    return pytz.timezone(user.time_zone or 'UTC')

def to_user_timezone(timestamp, user):
    """Convert UTC timestamp to user's timezone"""
    if not timestamp:
        return None
    if not timestamp.tzinfo:
        timestamp = pytz.UTC.localize(timestamp)
    return timestamp.astimezone(get_user_timezone(user))

def from_user_timezone(timestamp, user):
    """Convert timestamp from user's timezone to UTC"""
    if not timestamp:
        return None
    user_tz = get_user_timezone(user)
    if not timestamp.tzinfo:
        timestamp = user_tz.localize(timestamp)
    return timestamp.astimezone(pytz.UTC)

def now_in_utc():
    """Get current time in UTC"""
    return datetime.now(pytz.UTC)
