IGNORED_DIRECTORIES = {".git", "node_modules", ".venv", "dist", "build"}


def scan_repository_files(paths):
    """Keep source text while ignoring generated directories and binary files."""
    indexed = []
    for path in paths:
        if any(part in IGNORED_DIRECTORIES for part in path.parts):
            continue
        if path.is_binary:
            continue
        indexed.append(path)
    return indexed
