from datetime import date, datetime
from zoneinfo import ZoneInfo

BUSINESS_TIMEZONE = ZoneInfo("Asia/Shanghai")

def get_business_today() -> date:
    return datetime.now(BUSINESS_TIMEZONE).date()


def get_business_now() -> datetime:
    return datetime.now(BUSINESS_TIMEZONE)
