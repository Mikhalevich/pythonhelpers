#!/usr/bin/python

import time
import re
import argparse
import os
import os.path

REGEXP_TRANSLATIONS_PATTERN = r".*tr\s*\(\s*\"(.+)\"\s*\)"
REGEXP_INCLUDE_PATTERN = r"""\s*#\s*include\s*[\<\"](.+)[\>\"]\s*"""
REGEXP_CLASS_PATTERN = r"\s*class\s*([\w\d]+)\s*;\s*"

PATTERNS = (
    (REGEXP_TRANSLATIONS_PATTERN, 1, "translations"),
    (REGEXP_INCLUDE_PATTERN, 1, "includes"),
    (REGEXP_CLASS_PATTERN, 1, "class"),
)

ROOT_DIR = "../ViberDesktop/src"
#ROOT_DIR = "../VoiceEngine"
FILE_SUFFIX_TO_SCAN = (".h", ".cpp")


def scan_file(filename):
    file_duplicates = {}
    for pattern in PATTERNS:
        duplicates = {}
        strings = set()
        regexp_pattern = re.compile(pattern[0])
        captured_group = pattern[1]
        duplicates_description = pattern[2]

        with open(filename, "r") as file:
            for line in file:
                match = regexp_pattern.match(line)
                if match:
                    matched_string = match.group(captured_group)
                    if matched_string in strings:
                        duplicates[matched_string] = duplicates.get(matched_string, 1) + 1
                    else:
                        strings.add(matched_string)

        if len(duplicates) > 0:
            file_duplicates[duplicates_description] = duplicates

    return file_duplicates

def find_duplicates(rootdir):
    if len(rootdir) <= 0:
        return

    all_duplicates = {}

    for root, dirs, files in os.walk(rootdir):
        for file in files:
            if os.path.splitext(file)[1] in FILE_SUFFIX_TO_SCAN:
                filename = os.path.abspath(os.path.join(root, file))
                file_duplicates = scan_file(filename)
                if len(file_duplicates) > 0:
                    all_duplicates[filename] = file_duplicates

    for filename, file_duplicates in all_duplicates.iteritems():
        print("************** {0} ***************".format(filename))
        for description, duplicates in file_duplicates.iteritems():
            for duplicate, count in duplicates.iteritems():
                print("{0} -> {1} -> {2}".format(description, duplicate, count))

def main():
    parser = argparse.ArgumentParser(description="Find duplicates in translation file")
    parser.add_argument("-r", "--root", dest="root", required=False, default=ROOT_DIR, help="root dir to process")

    args = parser.parse_args()

    print("start...\n")

    start_time = time.time()
    find_duplicates(args.root)
    end_time = time.time()

    print("\nscript execution: {0} ms".format((end_time - start_time) * 1000))
    print("end...")

if __name__ == "__main__":
    main()