import time
from collections import defaultdict

from bot.config import (
    MAX_CONCURRENT_PER_USER,
    RATE_LIMIT_PER_DAY,
    RATE_LIMIT_PER_MINUTE,
    TEMPORARY_HOLD_MINUTES,
)


class MemoryRateLimiter:
    """Sliding-window Rate Limiter (Rules R-1, R-2, R-3, R-4)."""

    def __init__(self):
        self.user_minute_history: dict[int, list[float]] = defaultdict(list)
        self.user_day_history: dict[int, list[float]] = defaultdict(list)
        self.user_concurrent: dict[int, int] = defaultdict(int)
        self.user_violations: dict[int, list[float]] = defaultdict(list)
        self.user_temporary_hold: dict[int, float] = {}
        self.blocked_users: set[int] = set()

    def is_blocked(self, user_id: int) -> bool:
        """Aturan R-4: Pengguna dengan status blocked diabaikan."""
        return user_id in self.blocked_users

    def block_user(self, user_id: int):
        self.blocked_users.add(user_id)

    def acquire_concurrent(self, user_id: int) -> bool:
        """Aturan R-2: Maksimal 2 pemrosesan bersamaan per pengguna."""
        if self.user_concurrent[user_id] >= MAX_CONCURRENT_PER_USER:
            return False
        self.user_concurrent[user_id] += 1
        return True

    def release_concurrent(self, user_id: int):
        """Melepas slot pemrosesan bersamaan."""
        if self.user_concurrent[user_id] > 0:
            self.user_concurrent[user_id] -= 1

    def is_allowed(self, user_id: int) -> tuple[bool, int]:
        """Memeriksa apakah request pengguna diizinkan (Aturan R-1 & R-3).

        Returns: (is_allowed, seconds_to_wait)
        """
        now = time.time()

        # Check temporary hold (R-3)
        if user_id in self.user_temporary_hold:
            hold_until = self.user_temporary_hold[user_id]
            if now < hold_until:
                wait_sec = int(hold_until - now) + 1
                return False, wait_sec
            else:
                del self.user_temporary_hold[user_id]

        # R-1: Check 1-minute window
        min_timestamps = [
            ts for ts in self.user_minute_history[user_id] if now - ts < 60.0
        ]
        if len(min_timestamps) >= RATE_LIMIT_PER_MINUTE:
            self.register_violation(user_id, now)
            oldest = min_timestamps[0]
            wait_sec = int(60.0 - (now - oldest)) + 1
            self.user_minute_history[user_id] = min_timestamps
            return False, max(1, wait_sec)

        # R-1: Check 24-hour window
        day_timestamps = [
            ts for ts in self.user_day_history[user_id] if now - ts < 86400.0
        ]
        if len(day_timestamps) >= RATE_LIMIT_PER_DAY:
            self.register_violation(user_id, now)
            return False, 3600  # Coba lagi dalam 1 jam

        min_timestamps.append(now)
        day_timestamps.append(now)
        self.user_minute_history[user_id] = min_timestamps
        self.user_day_history[user_id] = day_timestamps
        return True, 0

    def register_violation(self, user_id: int, now: float):
        """Aturan R-3: 3 pelanggaran dalam 10 menit -> hold 15 menit."""
        violations = [
            ts for ts in self.user_violations[user_id] if now - ts < 600.0
        ]
        violations.append(now)
        self.user_violations[user_id] = violations

        if len(violations) >= 3:
            hold_seconds = TEMPORARY_HOLD_MINUTES * 60
            self.user_temporary_hold[user_id] = now + hold_seconds
            self.user_violations[user_id] = []


rate_limiter = MemoryRateLimiter()
