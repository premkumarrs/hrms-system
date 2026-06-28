from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from documents.validators import (
    BLOCKED_EXTENSIONS,
    validate_upload_file,
    safe_upload_filename,
)


class UploadValidatorTests(TestCase):

    def test_rejects_executable_extension(self):
        upload = SimpleUploadedFile('malware.exe', b'MZ fake', content_type='application/octet-stream')
        with self.assertRaises(Exception):
            validate_upload_file(upload)

    def test_rejects_oversized_file(self):
        upload = SimpleUploadedFile('big.pdf', b'%PDF' + b'x' * 6000000)
        with override_settings(HRMS_MAX_UPLOAD_BYTES=1024):
            with self.assertRaises(Exception):
                validate_upload_file(upload)

    def test_accepts_valid_pdf(self):
        upload = SimpleUploadedFile('letter.pdf', b'%PDF-1.4 test', content_type='application/pdf')
        validate_upload_file(upload)

    def test_safe_filename_strips_path(self):
        name = safe_upload_filename('../../evil.pdf')
        self.assertNotIn('..', name)
        self.assertTrue(name.endswith('.pdf'))

    def test_blocked_extensions_nonempty(self):
        self.assertIn('.exe', BLOCKED_EXTENSIONS)
