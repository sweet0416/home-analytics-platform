from datetime import date, timedelta


def count_business_days_since(nav_date: date, as_of_date: date) -> int:
    """Count weekdays after the NAV date through the observation date."""
    if nav_date >= as_of_date:
        return 0

    business_days = 0
    cursor = nav_date + timedelta(days=1)
    while cursor <= as_of_date:
        if cursor.weekday() < 5:
            business_days += 1
        cursor += timedelta(days=1)
    return business_days
