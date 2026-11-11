import argparse
import os
from pathlib import Path
import zipfile

LOG_FILES = ["error.log", "game.log", "gui_warnings.log", "debug.log"]
MAX_LINES = 400000


def count_lines(file_path: Path) -> int:
    with file_path.open("r", encoding="utf-8", errors="ignore") as f:
        return sum(1 for _ in f)


def split_log(file_path: Path, max_lines: int) -> list[Path]:
    created_files = []
    base_name = file_path.stem
    suffix = file_path.suffix

    with file_path.open("r", encoding="utf-8", errors="ignore") as infile:
        part_num = 1
        current_line = 0
        outfile = None
        out_path = None

        for line in infile:
            if current_line % max_lines == 0:
                if outfile:
                    outfile.close()
                    created_files.append(out_path)

                out_path = file_path.parent / f"{base_name}_part{part_num}{suffix}"
                outfile = out_path.open("w", encoding="utf-8")
                part_num += 1

            outfile.write(line)
            current_line += 1

        if outfile:
            outfile.close()
            created_files.append(out_path)

    return created_files


def default_log_dir() -> Path:
    profile = os.environ.get("AAWC_CK3_USER_DIR", "").strip()
    root = Path(profile).expanduser() if profile else Path.home() / "Documents" / "Paradox Interactive" / "Crusader Kings III"
    return root / "logs"


def main():
    parser = argparse.ArgumentParser(description="Package CK3 logs without modifying their source files.")
    parser.add_argument("--log-dir", type=Path, default=default_log_dir())
    parser.add_argument("--output", type=Path, default=Path.cwd() / "ck3_aawc_logs.zip")
    args = parser.parse_args()
    log_dir = args.log_dir.expanduser().resolve()
    output_zip = args.output.expanduser().resolve()
    files_to_zip = []

    for log_name in LOG_FILES:
        log_path = log_dir / log_name

        if not log_path.exists():
            print(f"Missing: {log_path}")
            continue

        line_count = count_lines(log_path)
        print(f"{log_name}: {line_count} lines")

        if line_count > MAX_LINES:
            print(f"Splitting {log_name}...")
            split_files = split_log(log_path, MAX_LINES)
            files_to_zip.extend(split_files)
        else:
            print(f"Keeping {log_name} as-is.")
            files_to_zip.append(log_path)

    output_zip.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file_path in files_to_zip:
            zf.write(file_path, arcname=file_path.name)
            print(f"Added to zip: {file_path.name}")

    print(f"Done. Created: {output_zip}")


if __name__ == "__main__":
    main()
