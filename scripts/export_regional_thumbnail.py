"""Lossy website encoding only; never edits or regenerates the native PNG.

The caller must retain this returned provenance with its integration transaction.
Existing destinations are reused only if a fresh, validated export is byte-identical;
different files are never overwritten. No manifest, registry, or page is changed here.
NumPy/SciPy enable full-resolution luminance SSIM; Pillow-only callers receive an
explicit unavailable status, while the always-measured PSNR/MAE gates still apply.
"""
from __future__ import annotations

import hashlib
import io
import math
import os
from pathlib import Path
import subprocess
import tempfile

from PIL import Image, ImageChops, ImageStat

try:
    import numpy as np
    from scipy.ndimage import uniform_filter
except ImportError:
    np = None
    uniform_filter = None


MAGICK = Path('/usr/bin/magick')
ENCODER_VERSION = '7.1.1-43'
ENCODER_ARGUMENTS = ('-sampling-factor', '4:4:4', '-interlace', 'Plane', '-quality', '92')
MIN_SSIM = 0.97
MIN_PSNR_DB = 35.0
MAX_MAE = 4.0


class ExportError(ValueError):
    """Invalid input, unsafe replacement, or failed fidelity validation."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _source_image(data: bytes) -> Image.Image:
    try:
        with Image.open(io.BytesIO(data)) as image:
            if image.format != 'PNG' or getattr(image, 'n_frames', 1) != 1:
                raise ExportError('Source must be a single-frame native PNG')
            image.load()
            if image.getexif().get(274, 1) != 1:
                raise ExportError('Nontrivial orientation metadata is not supported')
            if 'A' in image.getbands() or 'transparency' in image.info:
                if image.convert('RGBA').getchannel('A').getextrema() != (255, 255):
                    raise ExportError('Nonopaque transparency cannot be discarded')
            if image.mode not in ('RGB', 'RGBA'):
                raise ExportError('Source must use RGB or opaque RGBA pixels')
            if min(image.size) < 7:
                raise ExportError('Source must be at least 7 pixels in each dimension')
            return image.convert('RGB')
    except (OSError, SyntaxError) as exc:
        raise ExportError('Source does not decode as a valid PNG') from exc


def _output_image(data: bytes, size: tuple[int, int]) -> Image.Image:
    try:
        with Image.open(io.BytesIO(data)) as image:
            if image.format != 'JPEG' or image.mode != 'RGB':
                raise ExportError('Export must decode as RGB JPEG')
            image.load()
            if image.size != size:
                raise ExportError('Export dimensions differ from source')
            if not image.info.get('progressive') and not image.info.get('progression'):
                raise ExportError('Export is not progressive JPEG')
            sampling = [(item[1], item[2]) for item in getattr(image, 'layer', [])]
            if sampling != [(1, 1), (1, 1), (1, 1)]:
                raise ExportError('Export must use 4:4:4 chroma sampling')
            return image.copy()
    except (OSError, SyntaxError) as exc:
        raise ExportError('Export does not decode as a valid JPEG') from exc


def _metrics(source: Image.Image, output: Image.Image) -> dict:
    difference = ImageStat.Stat(ImageChops.difference(source, output))
    count = source.width * source.height * 3
    mae = sum(difference.sum) / count
    mse = sum(difference.sum2) / count
    # None denotes identical pixels (infinite PSNR), not a missing measurement.
    psnr = 10 * math.log10(255 * 255 / mse) if mse else None
    result = {
        'mean_absolute_channel_error_0_255': mae,
        'rmse_0_255': math.sqrt(mse),
        'psnr_db': psnr,
        'decoded_pixel_identical': mse == 0,
        'luminance_ssim_7x7': None,
        'ssim_status': 'unavailable: NumPy/SciPy not installed',
    }
    if np is not None and uniform_filter is not None:
        # Analysis only: full-resolution RGB luminance, uniform 7x7 windows,
        # sample covariance, and a 3px edge exclusion. No resized image is made.
        a = np.asarray(source, dtype=np.float64) @ np.array([0.299, 0.587, 0.114])
        b = np.asarray(output, dtype=np.float64) @ np.array([0.299, 0.587, 0.114])
        mean_a = uniform_filter(a, size=7)
        mean_b = uniform_filter(b, size=7)
        covariance_scale = 49 / 48
        variance_a = covariance_scale * (uniform_filter(a * a, size=7) - mean_a * mean_a)
        variance_b = covariance_scale * (uniform_filter(b * b, size=7) - mean_b * mean_b)
        covariance = covariance_scale * (uniform_filter(a * b, size=7) - mean_a * mean_b)
        c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
        scores = ((2 * mean_a * mean_b + c1) * (2 * covariance + c2)
                  / ((mean_a * mean_a + mean_b * mean_b + c1)
                     * (variance_a + variance_b + c2)))
        result['luminance_ssim_7x7'] = float(scores[3:-3, 3:-3].mean())
        result['ssim_status'] = 'measured: full-resolution luminance, 7x7 uniform, sample covariance'
    return result


def _validate_metrics(metrics: dict) -> None:
    ssim = metrics['luminance_ssim_7x7']
    psnr = metrics['psnr_db']
    mae = metrics['mean_absolute_channel_error_0_255']
    if ssim is not None and (not math.isfinite(ssim) or ssim < MIN_SSIM):
        raise ExportError(f'Export SSIM below {MIN_SSIM}: {ssim}')
    if psnr is not None and (not math.isfinite(psnr) or psnr < MIN_PSNR_DB):
        raise ExportError(f'Export PSNR below {MIN_PSNR_DB} dB: {psnr}')
    if not math.isfinite(mae) or mae > MAX_MAE:
        raise ExportError(f'Export mean absolute error exceeds {MAX_MAE}: {mae}')


def _encoder_version() -> str:
    if not MAGICK.is_file():
        raise ExportError(f'Required ImageMagick encoder is absent: {MAGICK}')
    result = subprocess.run([str(MAGICK), '-version'], check=True, capture_output=True,
                            text=True, timeout=15)
    version = result.stdout.splitlines()[0]
    if not version.startswith(f'Version: ImageMagick {ENCODER_VERSION} '):
        raise ExportError(f'Unapproved encoder version: {version}')
    return version


def export_thumbnail(source: Path, destination: Path) -> dict:
    """Export an opaque PNG without resizing; return JSON-safe measured provenance.

    ``destination`` must have a .jpg/.jpeg suffix and an existing parent directory.
    A differing existing destination raises ExportError; callers must choose a new
    path or handle an explicitly authorized replacement in their own transaction.
    Atomic creation is no-clobber, including a concurrent competing destination.
    """
    source = Path(source).resolve(strict=True)
    destination = Path(destination).absolute()
    if destination.suffix.lower() not in ('.jpg', '.jpeg'):
        raise ExportError('Destination must use a .jpg or .jpeg extension')
    if destination.is_symlink():
        raise ExportError('Destination must not be a symbolic link')
    if destination.resolve() == source or (destination.exists() and destination.samefile(source)):
        raise ExportError('Destination must not replace the source')
    if not destination.parent.is_dir():
        raise ExportError('Destination parent directory must already exist')
    if destination.exists() and not destination.is_file():
        raise ExportError('Destination must be a regular file')

    native = source.read_bytes()
    native_sha = _sha256(native)
    source_pixels = _source_image(native)
    version = _encoder_version()
    descriptor, name = tempfile.mkstemp(prefix='.regional-export-', suffix='.jpg',
                                        dir=destination.parent)
    os.close(descriptor)
    temporary = Path(name)
    try:
        command = [str(MAGICK), str(source), *ENCODER_ARGUMENTS, str(temporary)]
        process = subprocess.run(command, capture_output=True, text=True, timeout=120)
        if process.returncode:
            raise ExportError(f'ImageMagick failed: {process.stderr[:2000]}')
        encoded = temporary.read_bytes()
        output_pixels = _output_image(encoded, source_pixels.size)
        metrics = _metrics(source_pixels, output_pixels)
        _validate_metrics(metrics)
        if _sha256(source.read_bytes()) != native_sha:
            raise ExportError('Source changed during export; no destination was published')

        # link() exposes only the fully validated file and never replaces a file
        # another process created after the initial destination checks.
        reused = False
        try:
            os.link(temporary, destination)
        except FileExistsError:
            if destination.is_symlink() or not destination.is_file() or destination.read_bytes() != encoded:
                raise ExportError('Existing destination differs; refusing to overwrite')
            reused = True
        return {
            'source_sha256': native_sha,
            'source_bytes': len(native),
            'source_pixel_sha256': _sha256(source_pixels.tobytes()),
            'source_pixel_hash_format': 'decoded RGB bytes, row-major; dimensions recorded separately',
            'sha256': _sha256(encoded),
            'bytes': len(encoded),
            'pixel_sha256': _sha256(output_pixels.tobytes()),
            'width': output_pixels.width,
            'height': output_pixels.height,
            'mime_type': 'image/jpeg',
            'encoder': {
                'name': 'ImageMagick', 'version': version, 'executable': str(MAGICK),
                'arguments': list(ENCODER_ARGUMENTS),
                'quality': 92, 'chroma_sampling': '4:4:4', 'progressive': True,
                'resize': False, 'crop': False,
            },
            'metrics': metrics,
            'fidelity_thresholds': {'minimum_ssim': MIN_SSIM, 'minimum_psnr_db': MIN_PSNR_DB,
                                   'maximum_mae_0_255': MAX_MAE},
            'reused_existing': reused,
        }
    finally:
        temporary.unlink(missing_ok=True)
