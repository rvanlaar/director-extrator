import re
from io import BufferedReader
from pathlib import Path
from shutil import copy2
from subprocess import run
from sys import argv
from tempfile import TemporaryDirectory
from typing import Optional

from shock import extract_projector

PROJECTORRAYS = Path("../ProjectorRays/projectorrays").absolute()


def get_offset(regex: bytes, data: bytes) -> Optional[int]:
    found = re.search(regex, data, re.S)
    if found:
        return found.start()
    return None


def is_mac(data: bytes) -> Optional[int]:
    regex = rb"RIFX.{4}APPL"
    return get_offset(regex, data)


def is_win(data: bytes) -> Optional[int]:
    regex = rb"XFIR.{4}LPPA"
    return get_offset(regex, data)


def is_rifx(data: bytes) -> Optional[int]:
    regex = rb"(?:XFIR|RIFX).{4}(?:MV93|39VM)"
    offset = get_offset(regex, data)
    if offset:
        print("IS RIFX: CHECK WHAT THE ORIGINAL SHOULD BE DOING.")
    return offset


class ExtractFile:

    filetype: Optional[str]
    filename: Path
    file: BufferedReader
    offset: int

    def __init__(self, filename: Path):
        self.filename = filename
        self.file = filename.open("rb")
        self.filetype = None

    def determine_filetype(self) -> None:
        if self.filetype:
            # initialiation has been done already
            return
        data = self.file.read()
        offset = is_mac(data)
        if offset:
            self.filetype = "mac"
            self.offset = offset
            return
        offset = is_win(data)
        if offset:
            self.filetype = "mac"
            self.offset = offset
            return
        offset = is_rifx(data)
        if offset:
            self.filetype = "rifx"
            self.offset = offset
        return

    def is_director_file(self) -> bool:
        self.determine_filetype()
        return bool(self.filetype)


def is_projector_file(filename: Path) -> bool:
    return ExtractFile(filename).is_director_file()


def unprotect_filename(filename: Path) -> Path:
    conv = {".dcr": ".dir", ".dxr": ".dir", ".cxt": ".cst", ".cct": ".cst"}
    suffix = conv[filename.suffix.lower()]
    return filename.with_suffix(suffix)


def handle_projector_file(item: Path, output_dir: Path):
    with TemporaryDirectory() as tempdir:
        extract_projector(str(item), tempdir)
        for extracted_file in Path(tempdir).iterdir():
            handle_protected_file(extracted_file, output_dir)


def handle_protected_file(item: Path, output_dir: Path):
    output_item_dir = output_dir / item.stem
    if not output_item_dir.exists():
        output_item_dir.mkdir()
    run([PROJECTORRAYS, "decompile", "--dump-scripts", str(item), "-o", output_dir.absolute()], cwd=output_item_dir)


def handle_dir(input_dir: Path, output_dir: Path):
    if not output_dir.exists():
        output_dir.mkdir()
    for item in input_dir.iterdir():
        if item.is_dir():
            handle_dir(item.absolute(), output_dir / item.name)
        if item.is_file():
            if is_projector_file(item):
                print(f"{item} is Projector file")
                handle_projector_file(item.absolute(), output_dir)
            elif item.suffix.lower() in [".dxr", ".cxt"]:
                print(f"{item}: Protected director file")
                handle_protected_file(item.absolute(), output_dir)
            else:
                print(f"{item}: copied")
                copy2(str(item), str(output_dir / item.name))


def main():
    director_dir = Path(argv[1])
    output_dir = Path(argv[2])
    handle_dir(director_dir, output_dir)


if __name__ == "__main__":
    main()
