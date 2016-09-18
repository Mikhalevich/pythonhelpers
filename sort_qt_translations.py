#!/usr/bin/python

import time
import os.path
import re

DEBUG_START = "#ifdef _DEBUG"
DEBUG_END = "#endif"
QPROPERTY = "Q_PROPERTY"
REGEXP_PROPERTY_PATTERN = r"\s*Q_PROPERTY\s*\(\s*QString\s+(\w+)\s+READ\s+(\w+)\s+NOTIFY\s+(\w+)\s*\)\s*"
#REGEXP_METHOD_PATTERN = r"\s*QString\s+(w+)\s*\(\s*\)\s*const\s*;\s*"
REGEXP_METHOD_PATTERN = r"\s*QString\s+(w+)\s*\(\s*\)\s*const\s*;\s*"
QOBJECT = "Q_OBJECT"

def removeUselessLines(lines):
    index_to_remove = []
    for index, line in enumerate(lines):
        if index > 0:
            if len(line.strip()) <= 0 and len(lines[index - 1].strip()) <= 0:
                index_to_remove.append(index)

    for index in reversed(index_to_remove):
        del lines[index]


def joinProperties(properties):
    if len(properties) <= 0:
        return ""

    result = []
    for property in properties:
        result.append(property[1])

    return "".join(result)

def writeCppFile(filename, lines, properties, debugProperties):
    debugToWrite = True
    with open(filename, "w") as file:
        for line in lines:
            file.write(line)
            if QOBJECT in line:
                file.write("\n")
                file.write(joinProperties(properties))
            if DEBUG_START in line:
                if debugToWrite and len(debugProperties) > 0:
                    debugToWrite = False
                    file.write(joinProperties(debugProperties))

def findAndSortByPattern(lines, matchPattern):
    properties = []
    debugProperties = []
    debugSection = False
    index_to_remove = []
    pattern = re.compile(matchPattern)

    for index, line in enumerate(lines):
        if DEBUG_START in line:
            debugSection = True
        elif DEBUG_END in line:
            debugSection = False
        else:
            match = pattern.match(line)
            if match:
                print("{0} <<<<>>>>> {1}".format(line, match.group(1)))
                if debugSection:
                    debugProperties.append((match.group(1), line))
                else:
                    properties.append((match.group(1), line))
                index_to_remove.append(index)

    for index in reversed(index_to_remove):
        del lines[index]

    return sorted(properties), sorted(debugProperties)

def findQtProperties(lines):
    properties = []
    debugProperties = []
    debugSection = False
    index_to_remove = []
    pattern = re.compile(REGEXP_PROPERTY_PATTERN)

    for index, line in enumerate(lines):
        if DEBUG_START in line:
            debugSection = True
        elif DEBUG_END in line:
            debugSection = False
        elif QPROPERTY in line:
            match = pattern.match(line)
            if match:
                if debugSection:
                    debugProperties.append((match.group(1), line))
                else:
                    properties.append((match.group(1), line))
                index_to_remove.append(index)

    for index in reversed(index_to_remove):
        del lines[index]

    return sorted(properties), sorted(debugProperties)

def processSourceFile(filename):
    startFileSize = os.path.getsize(filename)

    with open(filename, "r") as file:
        lines = file.readlines()

    if len(lines) <= 0:
        print("file {0} is empty".format(filename))
        return

    #properties, debugProperties = findAndSortByPattern(lines, REGEXP_PROPERTY_PATTERN)
    methods, debugMethods = findAndSortByPattern(lines, REGEXP_METHOD_PATTERN)
    removeUselessLines(lines)
    outputFileName = filename + "_output"
    #writeCppFile(outputFileName, lines, properties, debugProperties)

    endFileSize = os.path.getsize(outputFileName)
    print("start file size = {0}\nend file size = {1}".format(startFileSize, endFileSize))

def main():
    print("start...")

    start_time = time.time()
    processSourceFile("Translations.h")
    end_time = time.time()

    print("script execution: {0} ms".format((end_time - start_time) * 1000))
    print("end...")

if __name__ == "__main__":
    main()