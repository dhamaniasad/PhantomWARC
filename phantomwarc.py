import subprocess
import socket
import os
import errno
from selenium import webdriver
from selenium.webdriver.common.proxy import ProxyType
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
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
PROX_ADDR = "127.0.0.1:%s" % warcprox_port


def initiate_warcprox(port):
    subprocess.call(["warcprox", "-p %s" % (warcprox_port), "-n warc", "-z",
                    "-d%s" % (WARC_DIR)])
initiate_warcprox(warcprox_port)


def start_browser(url):
    desired_capabilities = dict(DesiredCapabilities.PHANTOMJS)
    desired_capabilities["proxy"] = {"proxyType": ProxyType.MANUAL,
                                     "sslProxy": PROX_ADDR,
                                     "httpProxy": PROX_ADDR}
    browser = webdriver.PhantomJS(
        desired_capabilities=desired_capabilities,
        service_args=[
            "--proxy=%s" % PROX_ADDR,
            "--ssl-certificates-path=%s" % CERT_PATH,
            "--ignore-ssl-errors=true"])
    browser.implicitly_wait(2)
    browser.set_page_load_timeout(30)
    return browser
start_browser("https://www.google.com")
