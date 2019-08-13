#!/usr/bin/env python3

import time
import urllib.request
import urllib.error
import argparse
import os.path
import sys
import subprocess
import shutil
import re
from html.parser import HTMLParser

BUILD_DIRECTORY_URL = "http://builds.by.viberlab.com/builds/Viber/ViberPC/DevBuilds/"
BUILD_VERSION_SPLITTER = "."
BUILD_VERSION_SECTIONS = 4
BUILD_DEFAULT_INSTALLER_NAME = "DefaultViberSetup"
BUILD_DOWNLOAD_FOLDER = os.path.join(os.path.expanduser("~"), "Downloads")

PLATFORM_WIN = "Win"
PLATFORM_MAC = "Mac"
PLATFORM_LIN = "Lin"


class CustomError(RuntimeError):
    def __init__(self, error_message):
        self.message = error_message


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


def param_checker(*param_list):
    for param in param_list:
        if not param:
            raise CustomError("{0} is missing from config".format(param))


def urljoin(*args):
    return "/".join(s.lstrip("./").rstrip("/") for s in args)


class Configuration:
    def __init__(self, args):
        self.__platform = args.platform
        self.__version = args.version
        self.__fedora = args.fedora
        self.__build_type = self.__parse_build_type(args.type, args.platform, args.version)
        self.__init_platform_specific_parameters(args.platform)
        self.__store_path = args.spath
        self.__root_url = args.root
        self.__backup = args.backup
        self.__install = args.install
        self.__download = args.download

        if self.__install:
            current_platform = get_platform()
            if self.__platform != current_platform:
                print("You trying to install build for {0} on {1}".format(self.__platform, current_platform))
                self.__install = False
            self.__download = True

        if not os.path.isdir(self.__store_path):
            print("{0} is not a valid directory".format(self.__store_path))
            self.__store_path = "."

        param_checker(self.__platform,
                      self.__version,
                      self.__store_path,
                      self.__build_type,
                      self.__root_url)

    def __parse_build_type(self, type, platform, version):
        if type:
            return type
        if version.startswith("master"):
            return "Release"
        if platform == PLATFORM_LIN:
            return "Debug"
        return "QA"

    def __init_platform_specific_parameters(self, platform):
        if not platform:
            raise CustomError("Platform is undefined")
        if platform == PLATFORM_WIN:
            self.__installer_name = "ViberSetup.exe"
            self.__installed_path = os.path.join(os.path.expanduser("~"), "AppData/Local/Viber/Viber.exe")
            self.__db_path = os.path.join(os.path.expanduser("~"), "AppData/Roaming/ViberPC")
        elif platform == PLATFORM_MAC:
            self.__installer_name = "Viber.dmg"
            self.__installed_path = "/Applications/Viber.app/Contents/MacOS/Viber"
            self.__db_path = os.path.join(os.path.expanduser("~"), "Library/Application Support")
        elif platform == PLATFORM_LIN:
            if self.__fedora:
                self.__installer_name = "viber-{version}-{type}-x86_64.rpm"
            else:
                self.__installer_name = "viber_{version}_{type}_amd64.deb"
            self.__installed_path = "/opt/viber/Viber"
            self.__db_path = os.path.join(os.path.expanduser("~"), ".ViberPC")
        else:
            raise CustomError("Unknown platform specified: {}".format(platform))

    @property
    def platform(self):
        return self.__platform

    @property
    def root_url(self):
        return self.__root_url

    @property
    def version(self):
        return self.__version

    @property
    def build_type(self):
        return self.__build_type

    @property
    def store_path(self):
        return self.__store_path

    @property
    def install(self):
        return self.__install

    @property
    def download(self):
        return self.__download

    @property
    def backup(self):
        return self.__backup

    @property
    def installer_name(self):
        return self.__installer_name

    @property
    def installed_path(self):
        return self.__installed_path

    @property
    def db_path(self):
        return self.__db_path


class Processor:
    def __init__(self, configuration):
        self.__conf = configuration

    class BuildsParser(HTMLParser):
        def __init__(self, url, is_master, make_url_fun):
            super().__init__()
            self.__last_build = ""
            self.__fdd_revision = -1
            self.__url = url
            self.__is_master = is_master
            self.__make_url_fun = make_url_fun

        def handle_starttag(self, tag, attrs):
            if tag == 'a':
                for attr in attrs:
                    if attr[0] == 'href':
                        self.__parse_build(attr[1])
                        break

        @staticmethod
        def __get_master_version(build):
            match = re.search(r"(\d+)\.(\d+)\.(\d+)\.(\d+)", build.strip("./"))
            if not match:
                return tuple(0 for number in range(BUILD_VERSION_SECTIONS))  # (0, 0, 0, 0) for example
            return int(match.group(1)), int(match.group(2)), int(match.group(3)), int(match.group(4))

        @staticmethod
        def __get_fdd_version(build):
            match = re.search(r"[\-\w\d]+\.(\d+)", build.strip("./"))
            if not match:
                return -1
            return int(match.group(1))

        @staticmethod
        def __build_version(build):
            try:
                match = re.search(r"(\d+)\.(\d+)\.(\d+)\.(\d+)", build.strip("./"))
                if match:
                    return int(match.group(1)), int(match.group(2)), int(match.group(3)), int(match.group(4))

                match = re.search(r"[\-\w\d]+\.(\d+)", build.strip("./"))
                if match:
                    return int(match.group(1)), 0, 0, 0
            except ValueError:
                pass  # not int values

            return tuple(0 for number in range(BUILD_VERSION_SECTIONS))  # (0, 0, 0, 0) for example

        def __is_version_exists(self, version, revision):
            if not version:
                return False
            try:
                u = self.__make_url_fun(self.__url, version, revision)
                with urllib.request.urlopen(u) as response:
                    if response.getcode() == 200:  # page exists
                        return True
            except urllib.error.URLError as err:
                pass  # page not exists
            return False

        def __parse_build(self, build):
            if self.__is_master:
                if self.__get_master_version(build) > self.__get_master_version(self.__last_build):
                    if self.__is_version_exists(build, ""):
                        self.__last_build = build
            else:
                fdd_version = self.__get_fdd_version(build)
                if fdd_version > 0:
                    if fdd_version > self.__fdd_revision:
                        if self.__is_version_exists(build, str(fdd_version)):
                            self.__last_build = build
                            self.__fdd_revision = fdd_version

        def build(self):
            return self.__last_build

        def revision(self):
            if self.__fdd_revision < 0:
                return ""
            return str(self.__fdd_revision)

    def __last_build(self, build_directory_url):
        with urllib.request.urlopen(build_directory_url) as response:
            if response.getcode() != 200:
                raise CustomError("Invalid return code for url {}".format(build_directory_url))
            html_body = response.read()
            parser = self.BuildsParser(build_directory_url, self.__conf.version.startswith("master"), self.__make_download_url)
            parser.feed(html_body.decode("utf-8"))
            return parser.build(), parser.revision()
        return ""

    def __make_download_url(self, version_directory, build, revision):
        if self.__conf.platform == PLATFORM_LIN:
            installer_version = ""
            if revision:
                installer_version = revision
            else:
                installer_version = build.lstrip("./").rstrip("/")

            installer = self.__conf.installer_name.format(version=installer_version, type=self.__conf.build_type)
            download_url = urljoin(version_directory, build, self.__conf.platform, installer)
        else:
            download_url = urljoin(version_directory, build, self.__conf.platform, self.__conf.build_type, self.__conf.installer_name)
        return download_url

    def __download_build(self, url):
        with urllib.request.urlopen(url) as response:
            if response.getcode() != 200:
                raise CustomError("Invalid return code for url: ".format(url))

            file_name = url.rpartition("/")[2]
            if not file_name:
                print("Invalid file name use {0}".format(file_name))
                file_name = BUILD_DEFAULT_INSTALLER_NAME

            full_path = os.path.join(self.__conf.store_path, file_name)
            with open(full_path, "wb") as output:
                output.write(response.read())
        print("saved: {0}".format(os.path.abspath(full_path)))
        return full_path

    def __make_install_command(self, installer_path):
        if self.__conf.platform == PLATFORM_LIN:
            if self.__conf.__fedora:
                return ["sudo", "dnf", "install", installer_path]
            return ["sudo", "dpkg", "-i", installer_path]
        elif self.__conf.platform == PLATFORM_MAC:
            return ["open", installer_path]
        else:
            return installer_path

    def __is_viber_process_running(self):
        if self.__conf.platform == PLATFORM_LIN or self.__conf.platform == PLATFORM_MAC:
            try:
                pids = subprocess.check_output(["pgrep", "Viber"])
            except subprocess.CalledProcessError:
                print("viber is not running")
                return False

            if len(pids) > 0:
                return True
        elif self.__conf.platform == PLATFORM_WIN:  # some crappy code for windows
            process = subprocess.Popen('tasklist.exe /FO CSV /FI "IMAGENAME eq {0}"'.format("Viber.exe"),
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            out, err = process.communicate()
            try:
                return out.split("\n")[1].startswith('"Viber.exe"')
            except:
                return False

        return False

    def __stop_viber_process(self):
        if not os.path.exists(self.__conf.installed_path):
            return

        if self.__is_viber_process_running():
            ret_code = subprocess.call([self.__conf.installed_path, "ExitViber"])
            if ret_code != 0:
                raise CustomError("Invalid result code for viber: {0}".format(ret_code))

            sys.stdout.write("stoping viber process...")
            sys.stdout.flush()
            while True:
                time.sleep(1)
                if self.__is_viber_process_running():
                    sys.stdout.write(".")
                    sys.stdout.flush()
                else:
                    break

    def __backup_database(self, backup_folder):
        zip_name = os.path.join(backup_folder, time.strftime("%Y_%m_%d_Viber"))
        zip_name = shutil.make_archive(zip_name, "zip", self.__conf.db_path)
        return zip_name

    def __install_build(self, path, install_command):
        self.__stop_viber_process()

        if self.__conf.backup:
            print("backup in progress...")
            backup_folder = os.path.dirname(os.path.abspath(path))
            zip_name = self.__backup_database(backup_folder)
            if not zip_name:
                raise CustomError("Error was occurring during backup database")

            print("backup: {0}".format(zip_name))

        ret_code = subprocess.call(install_command)
        if ret_code != 0:
            raise CustomError("Invalid result code for installer: {0}".format(ret_code))

    def process(self):
        version_directory = urljoin(self.__conf.root_url, self.__conf.version)

        try:
            build, revision = self.__last_build(version_directory)
            if not build:
                raise CustomError("Unable to find build")
        except Exception as err:
            raise CustomError("Get build from server: {}".format(err))

        print("build: {0}".format(build))

        if self.__conf.download:
            try:
                download_url = self.__make_download_url(version_directory, build, revision)
                print("url: {0}".format(download_url))
                if not download_url:
                    raise CustomError("Download url is empty")

                installer_path = self.__download_build(download_url)
                if not installer_path:
                    raise CustomError("Error was occurred during download process")
            except Exception as err:
                raise CustomError("Download build: {}".format(err))

            if self.__conf.install:
                try:
                    install_command = self.__make_install_command(installer_path)
                    self.__install_build(installer_path, install_command)
                except Exception as err:
                    raise CustomError("Install build: {}".format(err))


def main():
    parser = argparse.ArgumentParser(description="Get last build from remote repository")
    parser.add_argument("-v", "--version", dest="version", required=True, help="build version to process")
    parser.add_argument("-d", "--download", dest="download", action="store_true", default=False, help="download flag for current version")
    parser.add_argument("-s", "--spath", dest="spath", required=False, default=BUILD_DOWNLOAD_FOLDER, help="store path for build")
    parser.add_argument("-t", "--type", dest="type", required=False, help="build type(Debug, Release, QA)")
    parser.add_argument("-p", "--platform", dest="platform", required=False, default=get_platform(), help="platform(Win, Mac, Lin)")
    parser.add_argument("-r", "--root", dest="root", required=False, default=BUILD_DIRECTORY_URL, help="root build directory url")
    parser.add_argument("-i", "--install", dest="install", action="store_true", default=False, help="trigger installation process")
    parser.add_argument("-b", "--backup", dest="backup", action="store_true", default=False, help="backup ViberPC folder")
    parser.add_argument("-f", "--fedora", dest="fedora", action="store_true", default=False, help="stub for fedora linux")
    args = parser.parse_args()

    start_time = time.time()
    try:
        p = Processor(Configuration(args))
        p.process()
        print("success")
    except CustomError as err:
        print("error: {}".format(err))
    end_time = time.time()

    print("script execution: {0} ms".format((end_time - start_time) * 1000))
    print("end...")


if __name__ == "__main__":
    main()
