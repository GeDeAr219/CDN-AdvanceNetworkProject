
from pathlib import Path

FILES_DIR = Path(__file__).resolve().parent / "files"

FILES_DIR.mkdir(exist_ok=True)

FILE_SIZE = 256 * 1024

for name in ["a", "b", "c", "d"]:

    filename = FILES_DIR / f"{name}.bin"

    content = name.encode() * FILE_SIZE

    filename.write_bytes(content)

    print(f"Created: {filename.name}")
    print(f"Size: {filename.stat().st_size} bytes")
