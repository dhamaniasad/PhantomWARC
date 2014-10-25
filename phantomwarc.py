import warcprox.warcprox as warcprox
from socket import error as socket_error
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.proxy import ProxyType
import os
import threading
import urlparse
import errno
import requests
import time
import logging

logger = logging.getLogger(__name__)
ROBOTS_TXT_TIMEOUT = 30  # seconds to wait before giving up on robots.txt
# seconds to wait before proceeding as though onLoad event fired
PAGE_LOAD_TIMEOUT = 60
# seconds before PhantomJS gives up running a DOM request (should be
# instant, assuming page is loaded)
ELEMENT_DISCOVERY_TIMEOUT = 2
# seconds to allow page to keep loading additional resources after onLoad
# event fires
AFTER_LOAD_TIMEOUT = 60
base_storage_path = os.getcwd()
user_agent = ''


def get_browser(user_agent, proxy_address, cert_path):
    """ Set up a Selenium browser with given user agent, proxy and SSL cert. """
    desired_capabilities = dict(DesiredCapabilities.PHANTOMJS)
    desired_capabilities["phantomjs.page.settings.userAgent"] = user_agent
    desired_capabilities["proxy"] = {
        "proxyType": ProxyType.MANUAL, "sslProxy": proxy_address, "httpProxy": proxy_address}
    browser = webdriver.PhantomJS(
        desired_capabilities=desired_capabilities,
        service_args=[
            "--proxy=%s" % proxy_address,
            "--ssl-certificates-path=%s" % cert_path,
            "--ignore-ssl-errors=true"])
    browser.implicitly_wait(ELEMENT_DISCOVERY_TIMEOUT)
    browser.set_page_load_timeout(ROBOTS_TXT_TIMEOUT)
    return browser


def proxy_capture(target_url):
    """
    start warcprox process. Warcprox is a MITM proxy server and needs to be running 
    before, during and after phantomjs gets a screenshot.

    Create an image from the supplied URL, write it to disk and update our asset model with the path.
    The heavy lifting is done by PhantomJS, our headless browser.

    This whole function runs with the local dir set to a temp dir by run_in_tempdir().
    So we can use local paths for temp files, and they'll just disappear when the function exits.
    """
    # basic setup

    warc_filename = 'archive.warc.gz'

    print "Fetching %s" % (target_url)

    # create a request handler class that counts unique requests and responses
    # global unique_requests, unique_responses
    unique_requests = set()
    unique_responses = set()
    count_lock = threading.Lock()

    class CountingRequestHandler(warcprox.WarcProxyHandler):

        def _proxy_request(self):
            #global unique_requests, unique_responses
            with count_lock:
                unique_requests.add(self.url)
            warcprox.WarcProxyHandler._proxy_request(self)
            with count_lock:
                unique_responses.add(self.url)

    # connect warcprox to an open port
    warcprox_port = 27500
    recorded_url_queue = warcprox.queue.Queue()
    fake_cert_authority = warcprox.CertificateAuthority()
    for i in xrange(500):
        try:
            proxy = warcprox.WarcProxy(
                server_address=("127.0.0.1", warcprox_port),
                ca=fake_cert_authority,
                recorded_url_q=recorded_url_queue,
                req_handler_class=CountingRequestHandler
            )
            break
        except socket_error as e:
            if e.errno != errno.EADDRINUSE:
                raise
        warcprox_port += 1
    else:
        raise self.retry(exc=Exception("WarcProx couldn't find an open port."))
    proxy_address = "127.0.0.1:%s" % warcprox_port

    # start warcprox in the background
    warc_writer = warcprox.WarcWriterThread(
        recorded_url_q=recorded_url_queue, gzip=True, port=warcprox_port)
    warcprox_controller = warcprox.WarcproxController(proxy, warc_writer)
    warcprox_thread = threading.Thread(
        target=warcprox_controller.run_until_shutdown, name="warcprox", args=())
    warcprox_thread.start()

    print "WarcProx opened."

    # fetch robots.txt in the background

    # fetch page in the background
    # (we'll give
    print "Fetching url."
    browser = get_browser(
        user_agent, proxy_address, fake_cert_authority.ca_file)
    browser.set_window_size(1024, 800)
    page_load_thread = threading.Thread(
        target=browser.get, args=(target_url,))  # returns after onload
    page_load_thread.start()
    page_load_thread.join(PAGE_LOAD_TIMEOUT)
    if page_load_thread.is_alive():
        print "Waited 60 seconds for onLoad event -- giving up."
        if not unique_responses:
            # if nothing at all has loaded yet, give up on the capture
            browser.quit()  # shut down phantomjs
            # send signal to shut down warc thread
            warcprox_controller.stop.set()
            warcprox_thread.join()
            return
    print "Finished fetching url."
    # (run this in a thread and give it long enough to find the tags, but then let other stuff proceed)
    # save preliminary screenshot immediately, and an updated version later
    # (we want to return results quickly, but also give javascript time to render final results)
    # make sure all requests are finished
    print "Waiting for post-load requests."
    start_time = time.time()
    time.sleep(min(AFTER_LOAD_TIMEOUT, 5))
    while len(unique_responses) < len(unique_requests):
        print "%s/%s finished" % (len(unique_responses), len(unique_requests))
        if time.time() - start_time > AFTER_LOAD_TIMEOUT:
            print "Waited %s seconds to finish post-load requests -- giving up." % AFTER_LOAD_TIMEOUT
            break
        time.sleep(.5)

    # teardown:
    print "Shutting down browser and proxies."
    browser.quit()  # shut down phantomjs
    warcprox_controller.stop.set()  # send signal to shut down warc thread
    # wait until warcprox thread is done writing out warc
    warcprox_thread.join()

    print "Saving WARC."

    # save generated warc file
    try:
        warc_path = os.path.join(
            base_storage_path/warcs)
        with open(warc_path, 'r+b') as file_:
            warc_name = file_.write(warc_filename)
    except Exception as e:
        logger.info("Web Archive File creation failed for %s: %s" %
                    (target_url, e))

    print "capture done."
