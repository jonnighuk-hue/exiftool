import time

from bot.config import RATE_LIMIT_CALLS, RATE_LIMIT_WINDOW


class MemoryRateLimiter:
    """Sliding-window rate limiter berbasis memori per Telegram user_id."""

    def __init__(
        self, calls: int = RATE_LIMIT_CALLS, window: int = RATE_LIMIT_WINDOW
    ):
        self.calls = calls
        self.window = window
        self.user_history: dict[int, list[float]] = {}

    def is_allowed(self, user_id: int) -> tuple[bool, int]:
        """Memeriksa apakah user_id diperbolehkan melakukan request.

        Returns: (is_allowed, seconds_to_wait)
        """
        now = time.time()
        timestamps = self.user_history.get(user_id, [])

        # Filter timestamp yang masih dalam rentang window
        valid_timestamps = [ts for ts in timestamps if now - ts < self.window]

        if len(valid_timestamps) >= self.calls:
            oldest = valid_timestamps[0]
            seconds_to_wait = int(self.window - (now - oldest)) + 1
            self.user_history[user_id] = valid_timestamps
            return False, max(1, seconds_to_wait)

        valid_timestamps.append(now)
        self.user_history[user_id] = valid_timestamps
        return True, 0


# Singleton instance
rate_limiter = MemoryRateLimiter()
