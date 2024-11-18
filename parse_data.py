import os
import lzma
import csv
import re
import sys


def parse_out_xz(file_path):
    """Parse the contents of an .out.xz file and return a dictionary of values."""
    with lzma.open(file_path, 'rt') as f:
        data = f.read()
    # Use regex to find each value in the file
    keys = ["n", "m", "mergeability1norm1", "mergeability1norm2",
            "mergeability2norm1", "mergeability2norm2", "modularity",
            "degree", "community_size", "cvr"]
    values = {}
    for key in keys:
        match = re.search(fr"{key}: ([\d\.\-e]+)", data)
        if match:
            values[key] = float(match.group(1))
        else:
            values[key] = None  # In case the key is missing
    return values


def parse_timeout_xz(file_path):
    """Parse the .timeout.xz file to find the User time (seconds) value."""
    with lzma.open(file_path, 'rt') as f:
        data = f.read()
    # Extract the 'User time (seconds)' value
    match = re.search(r"User time \(seconds\): ([\d\.]+)", data)
    return float(match.group(1)) if match else None


def create_csv_from_out_xz(folder_path, output_csv):
    """Create a CSV file from .out.xz and .timeout.xz files in a specified folder."""
    # Initialize the CSV file with column headers
    with open(output_csv, mode='w', newline='') as csv_file:
        fieldnames = ["filename", "n", "m", "mergeability1norm1", "mergeability1norm2",
                      "mergeability2norm1", "mergeability2norm2", "modularity",
                      "degree", "community_size", "cvr", "mergetool_runtime"]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()

        # Iterate through all .out.xz files in the folder
        for filename in os.listdir(folder_path):
            if filename.endswith(".out.xz"):
                # Remove '.out.xz' to get the base name
                base_filename = filename[:-7]
                out_file_path = os.path.join(folder_path, filename)
                timeout_file_path = os.path.join(
                    folder_path, f"{base_filename}.timeout.xz")

                # Parse the .out.xz file and add filename to the dictionary
                file_data = parse_out_xz(out_file_path)
                file_data["filename"] = filename

                # Check and parse the corresponding .timeout.xz file for runtime
                if os.path.exists(timeout_file_path):
                    file_data["mergetool_runtime"] = parse_timeout_xz(
                        timeout_file_path)
                else:
                    file_data["mergetool_runtime"] = None

                # Write the data to the CSV file
                writer.writerow(file_data)


if __name__ == "__main__":
    # Ensure that folder location and output csv name are provided
    if len(sys.argv) != 3:
        print("Usage: python script.py <folder_location> <output_csv>")
        sys.exit(1)

    folder_location = sys.argv[1]
    output_csv = sys.argv[2]
    create_csv_from_out_xz(folder_location, output_csv)
