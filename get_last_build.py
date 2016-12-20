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
PLATFORM_LIN = "Lin"

BUILD_PARAMETERS = { PLATFORM_WIN : { "installer_name" : "ViberSetup.exe",
                                      "installed_path" : os.path.join(os.path.expanduser("~"), "AppData/Local/Viber"),
                                      "db_path" : os.path.join(os.path.expanduser("~"), "AppData/Roaming/ViberPC") },
                     PLATFORM_MAC : { "installer_name" : "Viber.dmg",
                                      "installed_path" : "/Applications/Viber.app/Contents/MacOS/Viber",
                                      "db_path" : os.path.join(os.path.expanduser("~"), "Library/Application Support") },
                     PLATFORM_LIN : { "installer_name" : "viber_%version%_%type%_amd64.deb",
                                      "installed_path" : "/opt/viber/Viber",
                                      "db_path" : os.path.join(os.path.expanduser("~"), ".ViberPC") } }

def get_platform():
    if sys.platform.startswith("win"):
        return PLATFORM_WIN
    elif sys.platform.startswith("darwin"):
        return PLATFORM_MAC
    elif sys.platform.startswith("linux"):
        return PLATFORM_LIN
    else:
        print("{0} doesn't supported", sys.platform)

    return ""

def urljoin(*args):
    return "/".join(s.rstrip("/") for s in args)

def platform_settings(platform):
    if len(platform) <= 0:
        platform = get_platform()

    try:
        settings = BUILD_PARAMETERS[platform]
    except KeyError as keyError:
        print(keyError)
        return {}, ""

    return settings, platform

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
    def __init__(self, url, platform):
        HTMLParser.__init__(self)
        self.last_build = ""
        self.url = url
        self.platform = platform

    
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            for attr in attrs:
                if attr[0] == 'href':
                    self.parse_build(attr[1])
                    break
    
    def parse_build(self, build):
        if splitted_build(build) > splitted_build(self.last_build):
            try:
                response = urllib2.urlopen(urljoin(self.url, build, self.platform))
                if response.getcode() == 200: # page exists
                    self.last_build = build
            except urllib2.URLError as urlError:
                pass # page not exists
        
    def build(self):
        return self.last_build

def last_build(build_directory_url, platform):
    try:
        response = urllib2.urlopen(build_directory_url)
        if response.getcode() != 200:
            print("Invalid return code")
            return ""
        html_body = response.read()
        parser = BuildsParser(build_directory_url, platform)
        parser.feed(html_body)
        return parser.build()
        
    except urllib2.URLError as urlError:
        print(urlError)
    
    return ""

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

def is_viber_process_running(platform):
    if platform == PLATFORM_LIN or platform == PLATFORM_MAC:
        try:
            pids = subprocess.check_output(["pgrep", "Viber"])
        except subprocess.CalledProcessError:
            print("viber is not running")
            return False

        if len(pids) > 0:
            return True
    elif platform == PLATFORM_WIN: # some crappy code for windows
        process = subprocess.Popen('tasklist.exe /FO CSV /FI "IMAGENAME eq {0}"'.format("Viber.exe"),
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        out, err = process.communicate()
        try:
            return out.split("\n")[1].startswith('"Viber.exe"')
        except:
            return False

    return False

def stop_viber_process(platform, installed_path):
    if not os.path.exists(installed_path):
        return True

    if is_viber_process_running(platform):
        retCode = subprocess.call([installed_path, "ExitViber"])
        if retCode != 0:
            print("Invalid result code for viber: {0}".format(retCode))
            return False

        sys.stdout.write("stopring viber process...")
        sys.stdout.flush()
        while True:
            time.sleep(1)
            if is_viber_process_running(platform):
                sys.stdout.write(".")
                sys.stdout.flush()
            else:
                break

    return True

def backup_database(backup_folder, db_path):
    zip_name = os.path.join(backup_folder, time.strftime("%Y_%m_%d_Viber"))
    zip_name = shutil.make_archive(zip_name, "zip", db_path)
    return zip_name

def make_install_command(installer_path, platform):
    if platform == PLATFORM_LIN:
        return ["sudo", "dpkg", "-i", installer_path]
    elif platform == PLATFORM_MAC:
        return ["open", installer_path]
    else:
        return installer_path

def install_build(platform, settings, path, install_command, need_backup):
    if len(path) <= 0:
        print("Invalid installer path")
        return False

    if not stop_viber_process(platform, settings["installed_path"]):
        print("Error was occuring during stoping viber process")
        return False

    if need_backup:
        print("backup in progress...")
        backup_folder = os.path.dirname(os.path.abspath(path))
        zip_name = backup_database(backup_folder, settings["db_path"])
        if len(zip_name) <= 0:
            print("Error was occuring during buckuping database")
            return False
        print("backup: {0}".format(zip_name))

    try:
        retCode = subprocess.call(install_command)
    except OSError as osErr:
        print(osErr)
        return False

    if retCode != 0:
        print("Invalid result code for installer: {0}".format(retCode))
        return False

    return True

def make_build_name(base_name, platform, version, type):
    name = base_name.replace("%version%", version.rstrip("/")).replace("%type%", type)
    return name

def make_download_url(version_directory, build, platform, build_type, installer):
    if platform == PLATFORM_LIN:
        installer = make_build_name(installer, platform, build, build_type)
        download_url = urljoin(version_directory, build, platform, installer)
    else:
        download_url = urljoin(version_directory, build, platform, build_type, installer)

    return download_url

def process(args):
    settings, platform = platform_settings(args.platform)
    if len(settings) <= 0:
        print("Invalid platform for download and install")
        return False

    version_directory = urljoin(args.root, args.version)
    build = last_build(version_directory, platform)
    if len(build) <= 0:
        print("Cannot found {0} build on server".format(args.version))
        return False

    print("build: {0}".format(build))
    if args.download:
        installer = settings["installer_name"]
        buildType = args.type
        if len(buildType) <= 0:
            buildType = "Release"

        download_url = make_download_url(version_directory, build, platform, buildType, installer)
        print("url: {0}".format(download_url))
        if len(download_url) <= 0:
            print("Invalid url")
            return False

        installer_path = download_build(download_url, args.spath)
        if len(installer_path) <= 0:
            print("Error was occured during download process")

        if args.install:
            install_command = make_install_command(installer_path, platform)
            if not install_build(platform, settings, installer_path, install_command, args.backup):
                return False

    return True

def main():
    parser = argparse.ArgumentParser(description="Get last build from remote repository")
    parser.add_argument("-v", "--version", dest="version", required=True, help="build version to process")
    parser.add_argument("-d", "--download", dest="download", action="store_true", default=False, help="download flag for current version")
    parser.add_argument("-s", "--spath", dest="spath", required=False, default=BUILD_DOWNLOAD_FOLDER, help="store path for build")
    parser.add_argument("-t", "--type", dest="type", required=False, default="Release", help="build type(Debug, Release)")
    parser.add_argument("-p", "--platform", dest="platform", required=False, default=get_platform(), help="platform(Win, Mac, Lin)")
    parser.add_argument("-r", "--root", dest="root", required=False, default=BUILD_DIRECTORY_URL, help="root build directory url")
    parser.add_argument("-i", "--install", dest="install", action="store_true", default=False, help="trigger installation process")
    parser.add_argument("-b", "--backup", dest="backup", action="store_true", default=False, help="backup ViberPC folder")
    args = parser.parse_args()

    if args.install:
        current_platform = get_platform();
        if args.platform != current_platform:
            print("You trying to install build for {0} on {1}".format(args.platform, current_platform))
            args.install = False
        args.download = True

    start_time = time.time()
    if process(args):
        print("success")
    else:
        print("failure")
    end_time = time.time()

    print("script execution: {0} ms".format((end_time - start_time) * 1000))
    print("end...")

if __name__ == "__main__":
    main()
