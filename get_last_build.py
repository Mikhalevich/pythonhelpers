#!/usr/bin/python

import time
import urllib2
import argparse
import os.path
import sys
import subprocess
import shutil
from HTMLParser import HTMLParser

BUILD_DIRECTORY_URL = "http://builds.by.viberlab.com/builds/Viber/ViberPC/DevBuilds/"
BUILD_VERSION_SPLITTER = "."
BUILD_VERSION_SECTIONS = 4
BUILD_DEFAULT_INSTALLER_NAME = "DefaultViberSetup"
BUILD_DOWNLOAD_FOLDER = os.path.join(os.path.expanduser("~"), "Downloads")

PLATFORM_WIN = "Win"
PLATFORM_MAC = "Mac"

BUILD_PARAMETERS = { PLATFORM_WIN : { "name" : "ViberSetup.exe" },
                     PLATFORM_MAC : { "name" : "Viber.dmg" } }

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
            platform = PLATFORM_WIN
        elif sys.platform == "darwin":
            plaftorm = PLATFORM_MAC
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

def download_build(url, store_path):
    if len(url) <= 0:
        print("Invaild url to download")
        return ""

    if len(store_path) <= 0:
        print("Invalid store path")
        return ""

    if not os.path.isdir(store_path):
        print("{0} is not a valid directory".format(store_path))
        store_path = "."

    try:
        response = urllib2.urlopen(url)
        if response.getcode() != 200:
            print("Invalid return code")
            return ""

        file_name = url.rpartition("/")[2]
        if len(file_name) <= 0:
            file_name = BUILD_DEFAULT_INSTALLER_NAME
            print("Invalid file name use {0}".format(file_name))

        full_path = os.path.join(store_path, file_name)
        with open(full_path, "wb") as output:
            output.write(response.read())

        print("saved: {0}".format(os.path.abspath(full_path)))
    except urllib2.URLError as urlErr:
            print(urlErr)
            return ""
    except IndexError as indexErr:
            print(indexErr)
            return ""

    return full_path

def is_viber_process_running():
    # hardcoded for linux right now
    try:
        pids = subprocess.check_output(["pidof", "Viber"])
    except subprocess.CalledProcessError:
        print("Viber is not running")
        return False

    if len(pids) > 0:
        return True
    return False

def stop_viber_process():
    # hardcoded for linux righ now
    if not os.path.exists("/opt/viber/Viber"):
        return True

    if is_viber_process_running():
        retCode = subprocess.call(["/opt/viber/Viber", "ExitViber"])
        if retCode != 0:
            print("Invalid result code for viber: {0}".format(retCode))
            return False

        sys.stdout.write("stopring viber process...")
        sys.stdout.flush()
        while True:
            time.sleep(1)
            if is_viber_process_running():
                sys.stdout.write(".")
                sys.stdout.flush()
            else:
                break

    return True

def backup_database(backup_folder):
    zip_name = os.path.join(backup_folder, time.strftime("%Y_%m_%d_Viber"))
    zip_name = shutil.make_archive(zip_name, "zip", os.path.join(os.path.expanduser("~"), ".ViberPC"))
    return zip_name

def install_build(path, need_backup):
    if len(path) <= 0:
        print("Invalid installer path")
        return False

    if not stop_viber_process():
        print("Error was occuring during stoping viber process")
        return False

    if need_backup:
        print("backup in progress...")
        backup_folder = os.path.dirname(os.path.abspath(path))
        zip_name = backup_database(backup_folder)
        if len(zip_name) <= 0:
            print("Error was occuring during buckuping database")
            return False
        print("backup: {0}".format(zip_name))

    try:
        retCode = subprocess.call(path)
    except OSError as osErr:
        print(osErr)
        return False

    if retCode != 0:
        print("Invalid result code for installer: {0}".format(retCode))
        return False

    return True

def main():
    parser = argparse.ArgumentParser(description="Get last build from remote repository")
    parser.add_argument("-v", "--version", dest="version", required=True, help="build version to process")
    parser.add_argument("-d", "--download", dest="download", action="store_true", default=False, help="download flag for current version")
    parser.add_argument("-s", "--spath", dest="spath", required=False, default=BUILD_DOWNLOAD_FOLDER, help="store path for build")
    parser.add_argument("-t", "--type", dest="type", required=False, default="Release", help="build type(Debug, Release)")
    parser.add_argument("-p", "--platform", dest="platform", required=False, default=PLATFORM_WIN, help="platform(Win, Mac)")
    parser.add_argument("-r", "--root", dest="root", required=False, default=BUILD_DIRECTORY_URL, help="root build directory url")
    parser.add_argument("-i", "--install", dest="install", action="store_true", default=False, help="trigger installation process")
    parser.add_argument("-b", "--backup", dest="backup", action="store_true", default=False, help="backup ViberPC folder")
    args = parser.parse_args()

    start_time = time.time()

    version_directory = os.path.join(args.root, args.version)
    build = last_build(version_directory)
    if len(build) > 0:
        print("build: {0}".format(build))
        if args.download:
            url = generate_full_download_url(os.path.join(version_directory, build), args.type, args.platform)
            print("url: {0}".format(url))
            if len(url) > 0:
                installer_path = download_build(url, args.spath)
                if len(installer_path) > 0:
                    if args.install:
                        install_build(installer_path, args.backup)
                else:
                    print("Error was occured during download process")
    else:
        print("Cannot found {0} build on server".format(args.version))

    end_time = time.time()

    print("script execution: {0} ms".format((end_time - start_time) * 1000))
    print("end...")

if __name__ == "__main__":
    main()
