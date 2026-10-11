#!/usr/bin/env python3
"""Remove only known disposable output; never follow a symlink or clean host state."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent.parent

def main() -> int:
    for name in ('.build', 'dist'):
        target = ROOT / name
        if target.is_symlink():
            print(f'Refusing symlinked build output: {name}')
            return 1
    for name in ('.build', 'dist'):
        target = ROOT / name
        if target.is_dir():
            shutil.rmtree(target)
            print(f'Removed {name}/')
        elif target.exists():
            print(f'Refusing non-directory build output: {name}')
            return 1
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
