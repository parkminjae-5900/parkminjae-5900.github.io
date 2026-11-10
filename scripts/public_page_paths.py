"""Path-only guardrails for public page generators and search submissions.

Source fixtures are immutable test inputs, never pages on the production site.
Keep the fixture directory names in sync with _config.yml's Pages exclusions.
"""
from pathlib import PurePosixPath

FIXTURE_DIRECTORIES = frozenset({'tests', 'test', 'fixtures', '__tests__'})
NON_PUBLIC_DIRECTORIES = FIXTURE_DIRECTORIES | {
    'node_modules', 'vendor', 'dist', 'build', '_site',
}
ENRICHMENT_EXCLUDED_DIRECTORIES = {
    'quote-app', 'event-report', 'app', 'admin', 'staff', 'report',
}


def is_public_html_path(path):
    value = str(path)
    relative = PurePosixPath(value)
    return bool(
        value and '\\' not in value
        and not relative.is_absolute()
        and relative.suffix.lower() == '.html'
        and not any(part.startswith('.') or part.lower() in NON_PUBLIC_DIRECTORIES
                    for part in relative.parts)
    )


def is_enrichment_path(path):
    # Preserve the generator's pre-existing app/utility exclusions. Some of
    # these directories (e.g. the staff profile) are intentionally public.
    return is_public_html_path(path) and not any(
        part in ENRICHMENT_EXCLUDED_DIRECTORIES for part in PurePosixPath(path).parts)
