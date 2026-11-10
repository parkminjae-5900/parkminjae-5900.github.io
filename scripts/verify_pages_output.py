"""Check real Jekyll output, not just an exclusion setting in source control."""
import argparse
from pathlib import Path

from public_page_paths import FIXTURE_DIRECTORIES, is_public_html_path

ROOT = Path(__file__).resolve().parents[1]


def verify_output(destination, source=ROOT):
    if not destination.is_dir():
        raise ValueError('Pages build output does not exist: ' + str(destination))
    leaked = [p.relative_to(destination).as_posix()
              for p in destination.rglob('*')
              if any(part.lower() in FIXTURE_DIRECTORIES
                     for part in p.relative_to(destination).parts)]
    if leaked:
        raise ValueError('Test inputs leaked into Pages output: ' + ', '.join(leaked[:10]))
    # Removing source fixtures must not remove or change actual public documents.
    public_files = [p for p in source.rglob('*.html')
                    if is_public_html_path(p.relative_to(source).as_posix())]
    public_files += [source / name for name in (
        'sitemap.xml', 'robots.txt', 'CNAME', 'assets/regional-funeral-base.png',
        'data/funeral-hall-prices.json',
    )]
    for original in public_files:
        published = destination / original.relative_to(source)
        if not published.is_file():
            raise ValueError('Public file missing from Pages output: ' + str(published))
        if published.read_bytes() != original.read_bytes():
            raise ValueError('Public file changed by Pages build: ' + str(published))
    return len(public_files)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    count = verify_output(args.destination)
    print(f'Pages output excludes test inputs and preserves {count} public files.')
