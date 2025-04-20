import datetime
from zoneinfo import ZoneInfo
from typing import Union
import time

from dataIntegrator.common.CommonParameters import CommonParameters


class TimeUtility:
    """
    A utility class for handling various time-related operations.
    Note: Requires Python 3.9+ for zoneinfo functionality.
    """

    # Conversion methods
    @staticmethod
    def seconds_to_minutes(seconds: float) -> float:
        """Convert seconds to minutes."""
        return seconds / 60

    @staticmethod
    def minutes_to_seconds(minutes: float) -> float:
        """Convert minutes to seconds."""
        return minutes * 60

    @staticmethod
    def hours_to_minutes(hours: float) -> float:
        """Convert hours to minutes."""
        return hours * 60

    @staticmethod
    def days_to_hours(days: float) -> float:
        """Convert days to hours."""
        return days * 24

    # Formatting and parsing
    @staticmethod
    def format_time(
            timestamp: Union[datetime.datetime, float],
            format_str: str = "%Y-%m-%d %H:%M:%S"
    ) -> str:
        """
        Format a timestamp (datetime object or Unix timestamp) into a string.
        Unix timestamps are interpreted as UTC.
        """
        if isinstance(timestamp, datetime.datetime):
            dt = timestamp
        else:
            dt = datetime.datetime.utcfromtimestamp(timestamp)
        return dt.strftime(format_str)

    @staticmethod
    def parse_time_string(
            time_str: str,
            format_str: str = "%Y-%m-%d %H:%M:%S"
    ) -> datetime.datetime:
        """Parse a time string into a datetime object."""
        return datetime.datetime.strptime(time_str, format_str)

    # Time calculations
    @staticmethod
    def time_difference(
            start_dt: datetime.datetime,
            end_dt: datetime.datetime,
            unit: str = 'seconds'
    ) -> float:
        """Calculate difference between two datetimes in specified units."""
        delta = end_dt - start_dt
        total_seconds = delta.total_seconds()

        conversions = {
            'seconds': 1,
            'minutes': 60,
            'hours': 3600,
            'days': 86400
        }
        return total_seconds / conversions[unit]

    @staticmethod
    def add_time(
            dt: datetime.datetime,
            value: float,
            unit: str = 'seconds'
    ) -> datetime.datetime:
        """Add time to a datetime object."""
        conversions = {
            'seconds': datetime.timedelta(seconds=value),
            'minutes': datetime.timedelta(minutes=value),
            'hours': datetime.timedelta(hours=value),
            'days': datetime.timedelta(days=value)
        }
        return dt + conversions[unit]

    @staticmethod
    def subtract_time(
            dt: datetime.datetime,
            value: float,
            unit: str = 'seconds'
    ) -> datetime.datetime:
        """Subtract time from a datetime object."""
        conversions = {
            'seconds': datetime.timedelta(seconds=value),
            'minutes': datetime.timedelta(minutes=value),
            'hours': datetime.timedelta(hours=value),
            'days': datetime.timedelta(days=value)
        }
        return dt - conversions[unit]

    # Timezone handling
    @staticmethod
    def convert_timezone(
            dt: datetime.datetime,
            target_tz: str
    ) -> datetime.datetime:
        """Convert a datetime object to a different timezone."""
        if dt.tzinfo is None:
            raise ValueError("Naive datetime object requires timezone information")
        return dt.astimezone(ZoneInfo(target_tz))

    @staticmethod
    def get_current_time(timezone: str = CommonParameters.default_time_zone) -> datetime.datetime:
        """Get current time in specified timezone."""
        return datetime.datetime.now(ZoneInfo(timezone))

    @staticmethod
    def get_formatted_time_with_milliseconds():
        # 获取当前时间戳
        timestamp = time.time()
        # 计算毫秒部分
        milliseconds = int((timestamp - int(timestamp)) * 1000)
        # 获取当前时间（带时区）
        now = TimeUtility.get_current_time()
        # 格式化时间
        formatted_time = TimeUtility.format_time(now, "%Y-%m-%d %H:%M:%S")
        # 拼接时间与毫秒部分
        return f"{formatted_time}.{milliseconds:03d}"
