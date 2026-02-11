"""Enumerations for the email engine."""

import enum


class IPStatus(str, enum.Enum):
    ACTIVE = "active"
    RETIRING = "retiring"
    RESTING = "resting"
    WARMING = "warming"
    BLACKLISTED = "blacklisted"
    STANDBY = "standby"


class IPPurpose(str, enum.Enum):
    TRANSACTIONAL = "transactional"
    MARKETING = "marketing"
    COLD = "cold"
    STANDBY = "standby"


class WarmupPhase(str, enum.Enum):
    WEEK_1 = "week_1"
    WEEK_2 = "week_2"
    WEEK_3 = "week_3"
    WEEK_4 = "week_4"
    WEEK_5 = "week_5"
    WEEK_6 = "week_6"
    COMPLETED = "completed"


class AlertSeverity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertCategory(str, enum.Enum):
    BLACKLIST = "blacklist"
    HEALTH = "health"
    WARMUP = "warmup"
    ROTATION = "rotation"
    DNS = "dns"
    BOUNCE = "bounce"


class BounceType(str, enum.Enum):
    HARD = "hard"
    SOFT = "soft"
    COMPLAINT = "complaint"
