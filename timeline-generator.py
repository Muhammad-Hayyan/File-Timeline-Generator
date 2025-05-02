"""
File Timeline Generator

This script generates a timeline of file operations (creation, modification, access) 
from either a disk image or a folder and outputs the results to a CSV file.

Usage:
    python file_timeline.py --path "PATH" [--output OUTPUT] [--disk-image] [--recursive]

Arguments:
    --path PATH         Path to the disk image or folder to analyze (specify in double quotes "")
    --output OUTPUT     Output CSV file (default: timeline.csv)
    --disk-image        Specify if the path is a disk image 
    --recursive         Recursively scan folder contents 
    --date-sort         Sort events by timestamp

Example usage for analyzing folder:
    python timeline-generator.py --path "/path/to/folder" --output timeline.csv --recursive

Example usage for analyzing Disk Image:
    python timeline-generator.py --path "/path/to/image.E01" --output timeline.csv --disk-image
"""

import os
import csv
import argparse
import datetime
import sys
from typing import List, Dict, Any, Tuple

# Optional imports for disk image parsing
try:
    import pytsk3
    import pyewf

    DISK_IMAGE_SUPPORT = True
except ImportError:
    DISK_IMAGE_SUPPORT = False

# Class that handles EWF image files
if DISK_IMAGE_SUPPORT:

    class EWFImgInfo(pytsk3.Img_Info):

        def __init__(self, ewf_handle):
            self.ewf_handle = ewf_handle
            super(EWFImgInfo, self).__init__(url="", type=pytsk3.TSK_IMG_TYPE_EXTERNAL)

        def close(self):
            self.ewf_handle.close()

        def read(self, offset, size):
            self.ewf_handle.seek(offset)
            return self.ewf_handle.read(size)

        def get_size(self):
            return self.ewf_handle.get_media_size()


# Class representing a timeline entry for a file
class TimelineEntry:

    def __init__(self, path, name, size, created, modified, accessed, deleted=None):
        self.path = path
        self.name = name
        self.size = size
        self.created = created
        self.modified = modified
        self.accessed = accessed
        self.deleted = deleted

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "name": self.name,
            "size": self.size,
            "crtime": self.created,
            "mtime": self.modified,
            "atime": self.accessed,
            "deleted": self.deleted,
        }


def format_timestamp(timestamp) -> str:
    if timestamp is None:
        return ""

    if isinstance(timestamp, int) or isinstance(timestamp, float):
        try:
            dt = datetime.datetime.fromtimestamp(timestamp)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, OSError, OverflowError):
            return "Invalid timestamp"

    return str(timestamp)


def scan_folder(path: str, recursive: bool = False) -> List[TimelineEntry]:
    # Scan a folder for files and return timeline entries
    timeline_entries = []

    try:
        if recursive:
            for root, _, files in os.walk(path):
                for file in files:
                    file_path = os.path.join(root, file)
                    timeline_entries.append(process_file(file_path, root))
        else:
            for entry in os.listdir(path):
                entry_path = os.path.join(path, entry)
                if os.path.isfile(entry_path):
                    timeline_entries.append(process_file(entry_path, path))
    except PermissionError:
        print(f"Permission denied for path: {path}", file=sys.stderr)
    except Exception as e:
        print(f"Error scanning folder {path}: {e}", file=sys.stderr)

    return timeline_entries


def process_file(file_path: str, parent_path: str) -> TimelineEntry:
    # Process a file and create a timeline entry
    try:
        stat_info = os.stat(file_path)

        return TimelineEntry(
            path=parent_path,
            name=os.path.basename(file_path),
            size=stat_info.st_size,
            created=stat_info.st_ctime,
            modified=stat_info.st_mtime,
            accessed=stat_info.st_atime,
            deleted=None,
        )
    except Exception as e:
        print(f"Error processing file {file_path}: {e}", file=sys.stderr)
        return TimelineEntry(
            path=parent_path,
            name=os.path.basename(file_path),
            size=0,
            created=None,
            modified=None,
            accessed=None,
            deleted=None,
        )


def open_disk_image(image_path: str) -> Tuple[Any, Any]:
    # Open a disk image and return handle and image info
    if image_path.endswith(".E01") or image_path.endswith(".e01"):
        ewf_handle = pyewf.handle()
        ewf_handle.open([image_path])
        img_info = EWFImgInfo(ewf_handle)
    else:
        img_info = pytsk3.Img_Info(image_path)

    return img_info, None


def scan_disk_image(image_path: str) -> List[TimelineEntry]:
    # Scan a disk image for files and return timeline entries
    if not DISK_IMAGE_SUPPORT:
        print(
            "Error: Disk image parsing requires pytsk3 and pyewf libraries.",
            file=sys.stderr,
        )
        print("Install them with: pip install pytsk3 pyewf", file=sys.stderr)
        return []

    timeline_entries = []

    try:
        img_info, _ = open_disk_image(image_path)

        volume = pytsk3.Volume_Info(img_info)

        for partition in volume:
            if partition.len > 0:
                try:
                    fs_info = pytsk3.FS_Info(img_info, offset=partition.start * 512)
                    timeline_entries.extend(
                        process_directory(fs_info, fs_info.open_dir(path="/"))
                    )
                except Exception as e:
                    print(
                        f"Error processing partition {partition.addr}: {e}",
                        file=sys.stderr,
                    )
    except Exception as e:
        print(f"Error scanning disk image {image_path}: {e}", file=sys.stderr)

    return timeline_entries


def process_directory(fs_info, directory, parent_path="/") -> List[TimelineEntry]:
    timeline_entries = []

    try:
        for entry in directory:
            if entry.info.name.name in [b".", b".."]:
                continue

            try:
                file_name = entry.info.name.name.decode("utf-8")
            except UnicodeDecodeError:
                file_name = entry.info.name.name.decode("utf-8", errors="replace")

            file_path = os.path.join(parent_path, file_name)

            timeline_entry = TimelineEntry(
                path=parent_path,
                name=file_name,
                size=entry.info.meta.size if entry.info.meta else 0,
                created=entry.info.meta.crtime if entry.info.meta else None,
                modified=entry.info.meta.mtime if entry.info.meta else None,
                accessed=entry.info.meta.atime if entry.info.meta else None,
                deleted=None,
            )

            timeline_entries.append(timeline_entry)

            if (
                hasattr(entry.info, "type")
                and entry.info.type == pytsk3.TSK_FS_NAME_TYPE_DIR
            ):
                sub_directory = fs_info.open_dir(path=file_path)
                timeline_entries.extend(
                    process_directory(fs_info, sub_directory, file_path)
                )
    except Exception as e:
        print(f"Error processing directory {parent_path}: {e}", file=sys.stderr)

    return timeline_entries


def write_timeline_to_csv(timeline_entries: List[TimelineEntry], output_file: str):
    try:
        with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
            fieldnames = ["timestamp", "action", "path", "name", "size"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()

            for entry in timeline_entries:
                if entry.created:
                    writer.writerow(
                        {
                            "timestamp": format_timestamp(entry.created),
                            "action": "crtime",
                            "path": entry.path,
                            "name": entry.name,
                            "size": entry.size,
                        }
                    )

                if entry.modified:
                    writer.writerow(
                        {
                            "timestamp": format_timestamp(entry.modified),
                            "action": "mtime",
                            "path": entry.path,
                            "name": entry.name,
                            "size": entry.size,
                        }
                    )

                if entry.accessed:
                    writer.writerow(
                        {
                            "timestamp": format_timestamp(entry.accessed),
                            "action": "atime",
                            "path": entry.path,
                            "name": entry.name,
                            "size": entry.size,
                        }
                    )

                if entry.deleted:
                    writer.writerow(
                        {
                            "timestamp": format_timestamp(entry.deleted),
                            "action": "deleted",
                            "path": entry.path,
                            "name": entry.name,
                            "size": entry.size,
                        }
                    )

        print(f"Timeline written to {output_file}")
    except Exception as e:
        print(f"Error writing to CSV file {output_file}: {e}", file=sys.stderr)


def sort_timeline(output_file: str):
    try:
        with open(output_file, "r", newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            entries = list(reader)

        sorted_entries = sorted(
            entries, key=lambda x: x["timestamp"] if x["timestamp"] else "9999-99-99"
        )

        with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
            fieldnames = ["timestamp", "action", "path", "name", "size"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            writer.writerows(sorted_entries)
            print(f"timeline sorted")
    except Exception as e:
        print(f"Error sorting timeline in {output_file}: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Generate a timeline of file operations from a disk image or folder."
    )
    parser.add_argument(
        "--path", required=True, help="Path to the disk image or folder to analyze"
    )
    parser.add_argument(
        "--output",
        default="timeline.csv",
        help="Output CSV file (default: timeline.csv)",
    )
    parser.add_argument(
        "--disk-image", action="store_true", help="Specify if the path is a disk image"
    )
    parser.add_argument(
        "--recursive", action="store_true", help="Recursively scan folder contents"
    )
    parser.add_argument(
        "--date-sort", action="store_true", help="Sort events by timestamp"
    )

    args = parser.parse_args()

    if args.disk_image and not DISK_IMAGE_SUPPORT:
        print(
            "Error: Disk image parsing requires pytsk3 and pyewf libraries.",
            file=sys.stderr,
        )
        print("Install them with: pip install pytsk3 pyewf", file=sys.stderr)
        sys.exit(1)

    print(f"Analyzing {'disk image' if args.disk_image else 'folder'}: {args.path}")

    timeline_entries = []

    if args.disk_image:
        timeline_entries = scan_disk_image(args.path)
    else:
        timeline_entries = scan_folder(args.path, args.recursive)

    print(f"Found {len(timeline_entries)} files")

    write_timeline_to_csv(timeline_entries, args.output)
    if args.date_sort:
        sort_timeline(args.output)


if __name__ == "__main__":
    main()
