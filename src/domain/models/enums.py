"""Domain enums and constants"""

from enum import Enum


class PassengerType(Enum):
    """승객 유형"""
    ADULT = "adult"
    CHILD = "child"
    SENIOR = "senior"


class TrainType(Enum):
    """열차 유형"""
    KTX = "ktx"
    SRT = "srt"


class SeatPreference(Enum):
    """좌석 우선순위/제한 옵션"""

    GENERAL_FIRST = "general_first"
    SPECIAL_FIRST = "special_first"
    GENERAL_ONLY = "general_only"
    SPECIAL_ONLY = "special_only"
