"""Image discovery, with page numbers sorted like a human would expect."""

from pathlib import Path
import re

SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif'}


def image_files(folder: Path, include_pdf=False) -> list[Path]:
    extensions = SUPPORTED_EXTENSIONS | ({'.pdf'} if include_pdf else set())
    def natural_key(path: Path):
        return tuple(
            (1, int(part)) if part.isdigit() else (0, part.casefold())
            for part in re.split(r'(\d+)', path.name)
        ), path.name

    def collect(directory):
        entries = sorted(directory.iterdir(), key=natural_key)
        pages = [path for path in entries
                 if path.is_file() and path.suffix.lower() in extensions]
        # A folder's images form one chapter, even with PDFs between their names.
        # Order chapter groups by their first naturally sorted file.
        images = [path for path in pages if path.suffix.lower() != '.pdf']
        groups = [[path] for path in pages if path.suffix.lower() == '.pdf']
        if images:
            groups.append(images)
        groups.sort(key=lambda group: natural_key(group[0]))
        pages = [path for group in groups for path in group]
        for path in entries:
            # Do not follow directory links or Windows junctions into cycles.
            if path.is_dir() and not path.is_symlink() and not (
                hasattr(path, 'is_junction') and path.is_junction()
            ):
                pages.extend(collect(path))
        return pages

    return collect(folder)
