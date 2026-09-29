"""Действия контроллера."""
from enum import Enum


class Action(str, Enum):
    CONTINUE = "CONTINUE"
    SPLIT = "SPLIT"
    MERGE = "MERGE"
    COMPRESS = "COMPRESS"
    ARCHIVE = "ARCHIVE"
    REPLAN = "REPLAN"
    RETRIEVE = "RETRIEVE"
    VERIFY = "VERIFY"
    ROLLBACK = "ROLLBACK"
    STOP = "STOP"
