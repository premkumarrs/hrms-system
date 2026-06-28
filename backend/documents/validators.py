"""Upload validation for employee documents."""

import mimetypes
import os
import re
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.text import get_valid_filename

ALLOWED_EXTENSIONS = frozenset({
    '.pdf', '.doc', '.docx', '.png', '.jpg', '.jpeg', '.gif',
    '.xlsx', '.xls', '.csv', '.txt',
})

BLOCKED_EXTENSIONS = frozenset({
    '.exe', '.bat', '.cmd', '.com', '.msi', '.scr', '.ps1', '.vbs',
    '.js', '.jar', '.sh', '.dll', '.php', '.py', '.rb', '.pl',
    '.html', '.htm', '.svg', '.zip', '.rar', '.7z', '.gz',
})

ALLOWED_MIME_PREFIXES = (
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument',
    'application/vnd.ms-excel',
    'image/',
    'text/plain',
    'text/csv',
)

PDF_MAGIC = b'%PDF'


def max_upload_bytes():
    return getattr(settings, 'HRMS_MAX_UPLOAD_BYTES', 5 * 1024 * 1024)


def safe_upload_filename(original_name):
    """Return a sanitized, unique filename for storage."""

    base = get_valid_filename(os.path.basename(original_name or 'upload'))
    base = re.sub(r'[^\w.\-]', '_', base)
    if not base or base in ('.', '..'):
        base = 'upload'

    stem, ext = os.path.splitext(base)
    if not ext:
        ext = '.bin'

    unique = uuid.uuid4().hex[:8]
    return f"{stem[:80]}_{unique}{ext.lower()}"


def validate_upload_file(uploaded_file):
    """Raise ValidationError if the upload is unsafe or invalid."""

    if uploaded_file is None:
        raise ValidationError('No file was submitted.')

    size = getattr(uploaded_file, 'size', None)
    if size is None:
        uploaded_file.seek(0, os.SEEK_END)
        size = uploaded_file.tell()
        uploaded_file.seek(0)

    limit = max_upload_bytes()
    if size > limit:
        raise ValidationError(
            f'File exceeds maximum allowed size of {limit // (1024 * 1024)} MB.'
        )

    if size == 0:
        raise ValidationError('Empty files cannot be uploaded.')

    original = getattr(uploaded_file, 'name', '') or ''
    ext = os.path.splitext(original)[1].lower()

    if ext in BLOCKED_EXTENSIONS:
        raise ValidationError(f'File type "{ext}" is not permitted.')

    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            f'Unsupported file type "{ext}". '
            f'Allowed: {", ".join(sorted(ALLOWED_EXTENSIONS))}'
        )

    guessed, _ = mimetypes.guess_type(original)
    if guessed:
        if not any(
            guessed == prefix or guessed.startswith(prefix)
            for prefix in ALLOWED_MIME_PREFIXES
        ):
            raise ValidationError(f'MIME type "{guessed}" is not permitted.')

    head = uploaded_file.read(512)
    uploaded_file.seek(0)

    if ext == '.pdf' and not head.startswith(PDF_MAGIC):
        raise ValidationError('File does not appear to be a valid PDF.')

    if head[:2] == b'MZ':
        raise ValidationError('Executable files cannot be uploaded.')
