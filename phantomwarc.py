import subprocess
import socket
import os
import errno
from selenium import webdriver
from selenium.webdriver.common.proxy import *
import threading
BASE_DIR = os.getcwd()
WARC_DIR = BASE_DIR + "/warc/"
CERT_PATH = BASE_DIR + "warcprox-ca"


def make_sure_path_exists(path):
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise
make_sure_path_exists(WARC_DIR)

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind(('', 0))

warcprox_port = sock.getsockname()[1]
sock.close()
PROX_ADDR = "localhost:%s" % warcprox_port


def initiate_warcprox(port):
    subprocess.Popen(["warcprox", "-p %s" % (warcprox_port), "-nwarc", "-z",
                      "-d%s" % (WARC_DIR), "-j/dev/null"])
initiate_warcprox(warcprox_port)


def start_browsing():
    service_args = [
        '--proxy=%s' % PROX_ADDR,
        '--proxy-type=http, https',
    ]
    driver = webdriver.PhantomJS(service_args=service_args)
    driver.get("https://www.google.com")
start_browsing()
