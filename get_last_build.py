#!/usr/bin/python

import time
import urllib2
import argparse
import os.path
import sys
from HTMLParser import HTMLParser

BUILD_DIRECTORY_URL = "http://builds.by.viberlab.com/builds/Viber/ViberPC/DevBuilds/"
BUILD_VERSION_SPLITTER = "."
BUILD_VERSION_SECTIONS = 4
BUILD_DEFAULT_INSTALLER_NAME = "DefaultViberSetup"
BUILD_PARAMETERS = { "Win" : { "name" : "ViberSetup.exe" },
                     "Mac" : { "name" : "Viber.dmg" } }

def splitted_build(build):
    try:
        if len(build) > 0:
            stripped_build = build.rstrip("/")
            build_numbers = stripped_build.split(BUILD_VERSION_SPLITTER)
            if len(build_numbers) == BUILD_VERSION_SECTIONS:
                return tuple(int(c) for c in build_numbers)
    except ValueError:
        # not int values
        pass
    
    return tuple(0 for number in range(BUILD_VERSION_SECTIONS)) # (0, 0, 0, 0) for example

class BuildsParser(HTMLParser):
    last_build = ""
    
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            for attr in attrs:
                if attr[0] == 'href':
                    self.parse_build(attr[1])
                    break
    
    def parse_build(self, build):
        if splitted_build(build) > splitted_build(self.last_build):
            self.last_build = build
        
    def build(self):
        return self.last_build

def last_build(build_directory_url):
    try:
        response = urllib2.urlopen(build_directory_url)
        if response.getcode() != 200:
            print("Invalid return code")
            return ""
        html_body = response.read()
        parser = BuildsParser()
        parser.feed(html_body)
        return parser.build()
        
    except urllib2.URLError as urlError:
        print(urlError)
    
    return ""

def generate_full_download_url(version_directory, buildType, platform):
    if len(platform) <= 0:
        if sys.platform == "win32":
            platform = "Win"
        elif sys.platform == "darwin":
            plaftorm = "Mac"
        else:
            print("{0} doesn't supported", sys.platform)
            return ""

    try:
        installer = BUILD_PARAMETERS[platform]["name"]
    except KeyError as keyError:
        print(keyError)
        return ""

    if len(buildType) <= 0:
        buildType = "Release"

    return os.path.join(version_directory, platform, buildType, installer)

def download_build(url):
    if len(url) <= 0:
        print("Invaild url to download")
        return

    try:
        response = urllib2.urlopen(url)
        if response.getcode() != 200:
            print("Invalid return code")
            return False

        file_name = url.rpartition("/")[2]
        if len(file_name) <= 0:
            file_name = BUILD_DEFAULT_INSTALLER_NAME
            print("Invalid file name use {0}".format(file_name))

        with open(file_name, "wb") as output:
            output.write(response.read())

        print("{0} saved".format(file_name))
    except urllib2.URLError as urlErr:
            print(urlErr)
            return False
    except IndexError as indexErr:
            print(indexErr)
            return False

    return True

def main():
    parser = argparse.ArgumentParser(description="Get last build from remote repository")
    parser.add_argument("-v", "--version", dest="version", required=True, help="build version to process")
    parser.add_argument("-d", "--download", dest="download", action="store_true", default=False, help="download flag for current version")
    parser.add_argument("-t", "--type", dest="type", required=False, default="Release", help="build type(Debug, Release)")
    parser.add_argument("-p", "--platform", dest="platform", required=False, default="Win", help="platform(Win, Mac)")
    parser.add_argument("-r", "--root", dest="root", required=False, default=BUILD_DIRECTORY_URL, help="root build directory url")

    args = parser.parse_args()

    start_time = time.time()

    version_directory = os.path.join(args.root, args.version)
    build = last_build(version_directory)
    if len(build) > 0:
        print("build = {0}".format(build))
        if args.download:
            url = generate_full_download_url(os.path.join(version_directory, build), args.type, args.platform)
            if len(url) > 0:
                if download_build(url):
                    print("Downloaded...")
                else:
                    print("Error was occured durint download process")
    else:
        print("Cannot found {0} build on server".format(args.version))

    end_time = time.time()

    print("script execution: {0} ms".format((end_time - start_time) * 1000))
    print("end...")

if __name__ == "__main__":
    main()
