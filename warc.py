import warcprox.warcprox as warcprox
from socket import error as socket_error

class CountingRequestHandler(warcprox.WarcProxyHandler):
	def _proxy_request(self):
		with count_lock:
			unique_requests.add(self.url)
		warcprox.WarcProxyHandler._proxy_request(self)
		with count_lock:
			unique_responses.add(self.url)

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
