"""Exporter tests write disposable fixture pixels only, never production images."""
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import export_regional_thumbnail as exporter


def approved_encoder_available():
    try:
        exporter._encoder_version()
        return True
    except (OSError, ValueError, subprocess.SubprocessError):
        return False


def png_fixture(path, mode='RGB'):
    image = Image.new('RGB', (128, 96))
    image.putdata([(x * 2, y * 2, (x + y) % 256)
                   for y in range(96) for x in range(128)])
    image.convert(mode).save(path, format='PNG')


class ExportFixture(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.source = self.root / 'native.png'
        self.destination = self.root / 'website.jpg'
        png_fixture(self.source)

    def tearDown(self):
        self.temporary.cleanup()

    def assert_no_temporary_files(self):
        self.assertEqual(list(self.root.glob('.regional-export-*')), [])


class ValidationTests(ExportFixture):
    def test_rejects_non_png_even_with_png_extension(self):
        Image.new('RGB', (32, 32)).save(self.source, format='JPEG')
        with self.assertRaisesRegex(exporter.ExportError, 'native PNG'):
            exporter.export_thumbnail(self.source, self.destination)
        self.assertFalse(self.destination.exists())

    def test_rejects_corrupt_source(self):
        self.source.write_bytes(b'not an image')
        with self.assertRaisesRegex(exporter.ExportError, 'valid PNG'):
            exporter.export_thumbnail(self.source, self.destination)

    def test_rejects_nonopaque_alpha(self):
        Image.new('RGBA', (32, 32), (120, 150, 180, 254)).save(self.source)
        with self.assertRaisesRegex(exporter.ExportError, 'transparency'):
            exporter.export_thumbnail(self.source, self.destination)
        self.assertFalse(self.destination.exists())

    def test_rejects_palette_transparency(self):
        Image.new('P', (32, 32)).save(self.source, transparency=0)
        with self.assertRaisesRegex(exporter.ExportError, 'transparency'):
            exporter.export_thumbnail(self.source, self.destination)

    def test_rejects_wrong_destination_extension(self):
        before = self.source.read_bytes()
        with self.assertRaisesRegex(exporter.ExportError, 'extension'):
            exporter.export_thumbnail(self.source, self.source)
        self.assertEqual(self.source.read_bytes(), before)

    def test_rejects_source_alias(self):
        self.destination.hardlink_to(self.source)
        with self.assertRaisesRegex(exporter.ExportError, 'replace the source'):
            exporter.export_thumbnail(self.source, self.destination)

    def test_rejects_destination_symlink(self):
        self.destination.symlink_to(self.source)
        with self.assertRaisesRegex(exporter.ExportError, 'symbolic link'):
            exporter.export_thumbnail(self.source, self.destination)

    def test_missing_encoder_explicit(self):
        with patch.object(exporter, 'MAGICK', self.root / 'missing-magick'):
            with self.assertRaisesRegex(exporter.ExportError, 'encoder is absent'):
                exporter.export_thumbnail(self.source, self.destination)
        self.assert_no_temporary_files()

    def test_failed_encoder_leaves_no_output_or_temporary(self):
        result = subprocess.CompletedProcess([], 1, '', 'test encoder failure')
        with patch.object(exporter, '_encoder_version', return_value='test'), \
                patch.object(exporter.subprocess, 'run', return_value=result):
            with self.assertRaisesRegex(exporter.ExportError, 'ImageMagick failed'):
                exporter.export_thumbnail(self.source, self.destination)
        self.assertFalse(self.destination.exists())
        self.assert_no_temporary_files()

    def test_encoder_timeout_cleans_temporary(self):
        with patch.object(exporter, '_encoder_version', return_value='test'), \
                patch.object(exporter.subprocess, 'run', side_effect=subprocess.TimeoutExpired('magick', 120)):
            with self.assertRaises(subprocess.TimeoutExpired):
                exporter.export_thumbnail(self.source, self.destination)
        self.assertFalse(self.destination.exists())
        self.assert_no_temporary_files()

    def test_wrong_format_dimensions_sampling_and_progression_rejected(self):
        cases = [
            ('PNG', {}, 'RGB JPEG', (32, 32)),
            ('JPEG', {'progressive': True, 'subsampling': 0}, 'dimensions', (31, 32)),
            ('JPEG', {'progressive': False, 'subsampling': 0}, 'progressive', (32, 32)),
            ('JPEG', {'progressive': True, 'subsampling': 2}, '4:4:4', (32, 32)),
        ]
        for fmt, arguments, message, size in cases:
            with self.subTest(message=message):
                data = io.BytesIO()
                Image.new('RGB', size).save(data, format=fmt, **arguments)
                with self.assertRaisesRegex(exporter.ExportError, message):
                    exporter._output_image(data.getvalue(), (32, 32))

    def test_low_ssim_rejected(self):
        with self.assertRaisesRegex(exporter.ExportError, 'SSIM'):
            exporter._validate_metrics({'luminance_ssim_7x7': 0.969,
                                       'psnr_db': 42.0, 'mean_absolute_channel_error_0_255': 1.0})

    def test_pillow_only_metrics_are_honest(self):
        a = Image.new('RGB', (16, 16), (100, 100, 100))
        b = Image.new('RGB', (16, 16), (101, 101, 101))
        with patch.object(exporter, 'np', None), patch.object(exporter, 'uniform_filter', None):
            metrics = exporter._metrics(a, b)
        self.assertIsNone(metrics['luminance_ssim_7x7'])
        self.assertIn('unavailable', metrics['ssim_status'])
        self.assertEqual(metrics['mean_absolute_channel_error_0_255'], 1)
        self.assertAlmostEqual(metrics['psnr_db'], 48.1308, places=4)
        json.dumps(metrics, allow_nan=False)

    def test_identical_metrics_are_json_safe(self):
        with Image.open(self.source) as image:
            metrics = exporter._metrics(image, image)
        self.assertEqual(metrics['mean_absolute_channel_error_0_255'], 0)
        self.assertTrue(metrics['decoded_pixel_identical'])
        self.assertIsNone(metrics['psnr_db'])
        if metrics['luminance_ssim_7x7'] is not None:
            self.assertAlmostEqual(metrics['luminance_ssim_7x7'], 1)
        json.dumps(metrics, allow_nan=False)


@unittest.skipUnless(approved_encoder_available(), 'Approved ImageMagick encoder is not installed')
class EncoderTests(ExportFixture):
    def test_source_unchanged_and_valid_high_fidelity_export(self):
        before = self.source.read_bytes()
        record = exporter.export_thumbnail(self.source, self.destination)
        self.assertEqual(self.source.read_bytes(), before)
        self.assertEqual(record['source_sha256'], hashlib.sha256(before).hexdigest())
        self.assertEqual(record['source_bytes'], len(before))
        with Image.open(self.source) as image:
            self.assertEqual(record['source_pixel_sha256'], hashlib.sha256(image.convert('RGB').tobytes()).hexdigest())
        self.assertEqual((record['width'], record['height']), (128, 96))
        self.assertEqual(record['mime_type'], 'image/jpeg')
        self.assertEqual(record['sha256'], hashlib.sha256(self.destination.read_bytes()).hexdigest())
        self.assertEqual(record['bytes'], self.destination.stat().st_size)
        self.assertIn(exporter.ENCODER_VERSION, record['encoder']['version'])
        self.assertEqual(record['encoder']['arguments'], list(exporter.ENCODER_ARGUMENTS))
        self.assertGreater(record['metrics']['psnr_db'], 35)
        if record['metrics']['luminance_ssim_7x7'] is not None:
            self.assertGreaterEqual(record['metrics']['luminance_ssim_7x7'], 0.97)
        with Image.open(self.destination) as image:
            self.assertEqual(image.format, 'JPEG')
            self.assertTrue(image.info.get('progressive') or image.info.get('progression'))
            self.assertEqual([(item[1], item[2]) for item in image.layer], [(1, 1)] * 3)
        json.dumps(record, allow_nan=False)
        self.assert_no_temporary_files()

    def test_opaque_rgba_is_supported(self):
        png_fixture(self.source, mode='RGBA')
        before = self.source.read_bytes()
        exporter.export_thumbnail(self.source, self.destination)
        self.assertEqual(self.source.read_bytes(), before)

    def test_identical_existing_export_is_reused_without_rewrite(self):
        first = exporter.export_thumbnail(self.source, self.destination)
        stamp = self.destination.stat().st_mtime_ns
        second = exporter.export_thumbnail(self.source, self.destination)
        self.assertFalse(first['reused_existing'])
        self.assertTrue(second['reused_existing'])
        self.assertEqual(first['sha256'], second['sha256'])
        self.assertEqual(self.destination.stat().st_mtime_ns, stamp)
        self.assert_no_temporary_files()

    def test_different_existing_destination_is_never_overwritten(self):
        existing = b'existing user file'
        self.destination.write_bytes(existing)
        with self.assertRaisesRegex(exporter.ExportError, 'refusing to overwrite'):
            exporter.export_thumbnail(self.source, self.destination)
        self.assertEqual(self.destination.read_bytes(), existing)
        self.assert_no_temporary_files()

    def test_low_ssim_is_not_published(self):
        with patch.object(exporter, '_metrics', return_value={
                'luminance_ssim_7x7': 0.96, 'psnr_db': 42, 'mean_absolute_channel_error_0_255': 1}):
            with self.assertRaisesRegex(exporter.ExportError, 'SSIM'):
                exporter.export_thumbnail(self.source, self.destination)
        self.assertFalse(self.destination.exists())
        self.assert_no_temporary_files()

    def test_source_changed_during_encoding_is_not_published(self):
        real_run = subprocess.run

        def mutate_after_encoding(command, **kwargs):
            result = real_run(command, **kwargs)
            if '-quality' in command:
                with self.source.open('ab') as handle:
                    handle.write(b'fixture concurrent change')
            return result

        with patch.object(exporter.subprocess, 'run', side_effect=mutate_after_encoding):
            with self.assertRaisesRegex(exporter.ExportError, 'Source changed'):
                exporter.export_thumbnail(self.source, self.destination)
        self.assertFalse(self.destination.exists())
        self.assert_no_temporary_files()


if __name__ == '__main__':
    unittest.main()
