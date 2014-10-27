import subprocess
import socket
import os
import errno
import random
import string
import time
from internetarchive import get_item
from selenium import webdriver
from selenium.webdriver.common.proxy import ProxyType
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WARC_NAME = ''.join(random.choice(string.ascii_uppercase)
                    for i in range(10))
RAND_STR = WARC_NAME
WARC_NAME = WARC_NAME + ".warc.gz"
WARC_FILE = WARC_NAME
WARC_DIR = BASE_DIR + "/warc/"
WARC_NAME = WARC_DIR + WARC_NAME
CDX_NAME = WARC_DIR + RAND_STR + ".cdx"


def getfreesocket():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('', 0))
    proxy_port = sock.getsockname()[1]
    sock.close()
    return proxy_port


def make_sure_path_exists(path):
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise


def init_proxy(proxy_port):
    os.chdir("WarcMITMProxy")
    subprocess.Popen(["python", "warcmitmproxy.py", "-p %s" % proxy_port,
                      "-f%s" % WARC_NAME])


def cdx_generator():
    subprocess.Popen(["cdx-indexer", "%s" % CDX_NAME, "%s" % WARC_NAME])


def upload_to_ia():
    item = get_item(WARC_FILE)
    md = dict(mediatype='warc', creator='PhantomWARC')
    cdxmd = dict(mediatype='cdx', creator='PhantomWARC')
    item.upload(WARC_NAME, metadata=md, access_key=os.environ['IAS3_ACCESS_KEY'], secret_key=os.environ['IAS3_SECRET_KEY'])
    item.upload(CDX_NAME, metadata=cdxmd, access_key=os.environ['IAS3_ACCESS_KEY'], secret_key=os.environ['IAS3_SECRET_KEY'])
    IAURL = "https://archive.org/details/%s" % WARC_FILE
    print "WARC and CDX files uploaded to the Internet Archive as %s" % IAURL


def init_browser(url, ia=None):
    make_sure_path_exists(WARC_DIR)
    proxy_port = getfreesocket()
    PROX_ADDR = "127.0.0.1:%s" % proxy_port
    init_proxy(proxy_port)
    desired_capabilities = dict(DesiredCapabilities.PHANTOMJS)
    desired_capabilities["proxy"] = {"proxyType": ProxyType.MANUAL,
                                     "sslProxy": PROX_ADDR,
                                     "httpProxy": PROX_ADDR}
    desired_capabilities["phantomjs.page.settings.userAgent"] = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/37.0.2062.120 Chrome/37.0.2062.120 Safari/537.36")
    browser = webdriver.PhantomJS(
        desired_capabilities=desired_capabilities,
        service_args=[
            "--proxy=%s" % PROX_ADDR,
            "--ignore-ssl-errors=true"])
    browser.implicitly_wait(2)
    browser.set_page_load_timeout(30)
    browser.get(url)
    time.sleep(4)
    cdx_generator()
    print "WARC file generated as %s" % WARC_NAME
    print "CDX file generated as %s" % CDX_NAME
    if ia is True:
        upload_to_ia()
