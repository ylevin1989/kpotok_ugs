from enum import Enum


class GenerationType(str, Enum):
    INITIAL = 'initial'
    REVISION = 'revision'
    MANUAL_EDIT = 'manual_edit'
    QUALITY_FIX = 'quality_fix'


class ExportFormat(str, Enum):
    MARKDOWN = 'markdown'
    CSV = 'csv'
    ZIP = 'zip'


class ExportStatus(str, Enum):
    PENDING = 'pending'
    READY = 'ready'
    FAILED = 'failed'
