from enum import Enum


class GenerationType(str, Enum):
    INITIAL = 'initial'
    REVISION = 'revision'
    MANUAL_EDIT = 'manual_edit'
    QUALITY_FIX = 'quality_fix'
