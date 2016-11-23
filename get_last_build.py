#!/usr/bin/python

import time
import urllib2
from HTMLParser import HTMLParser

BUILD_DIRECTORY_URL = "http://localhost:8080/test"

def splitted_build(build):
    try:
        if len(build) > 0:
            build_numbers = build.split(".")
            if len(build_numbers) == 4:
                return tuple(int(c) for c in build_numbers)
    except ValueError:
        # not int values
        pass
    
    return (0, 0, 0, 0)

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

def main():
    start_time = time.time()
    print("build = {0}".format(last_build(BUILD_DIRECTORY_URL)))
    end_time = time.time()

    print("script execution: {0} ms".format((end_time - start_time) * 1000))
    print("end...")

if __name__ == "__main__":
    main()