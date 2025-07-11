[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

# File Timeline Generator

A Forensics Python tool that parses disk images or directories to create comprehensive CSV timeline reports of file operations (creation, modification, and access times).

## Features

- **Dual-mode operation**: Analyze regular file system directories or forensic disk images
- **Timeline generation**: Create timelines of file creation, modification, and access events
- **CSV output**: Easily viewable and parsable timeline format for further analysis
- **Recursive scanning**: Option to analyze entire directory trees
- **Disk image support**: Parse E01 (EnCase) and raw disk image formats
- **Cross-platform**: Works on Windows, macOS, and Linux

## Installation

### Prerequisites

- Python 3.6 or higher
- For disk image analysis (optional):
  - pytsk3
  - pyewf

### Installation

1. Clone this repository:
   ```
   git clone https://github.com/Muhammad-Hayyan/File-Timeline-Generator.git
   cd File-Timeline-Generator
   ```

2. Install the additional dependencies:
   ```
   pip install pytsk3 pyewf
   ```

## Usage

### Basic Command Format

```
python file_timeline.py --path "PATH" [--output "OUTPUT"] [--disk-image] [--recursive]
```

### Arguments

- `--path PATH`: Path to the disk image or folder to analyze (use quotes for paths with spaces)
- `--output OUTPUT`: Output CSV file (default: timeline.csv)
- `--disk-image`: Specify if the path is a disk image
- `--recursive`: Recursively scan folder contents
- `--date-sort`: Sort events by timestamp (optional)

### Examples

Analyze a folder:
```
python timeline-generator.py --path "/path/to/folder" --output "timeline.csv" --recursive --date-sort
```
Analyze a disk image:
```
python timeline-generator.py --path "/path/to/image.E01" --output "disk_timeline.csv" --disk-image
```

## Output Format

The tool generates a CSV file with the following columns:

- **timestamp**: Date and time of the event in YYYY-MM-DD HH:MM:SS format
- **action**: Type of action ( crtime: created, mtime: modified, atime: accessed)
- **path**: Directory path containing the file
- **name**: Filename
- **size**: File size in bytes

## License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**This tool currently doesn't support AFF, VHD, VMDK and VDI Disk image formats. I will Upload an advance version of this tool soon.**


