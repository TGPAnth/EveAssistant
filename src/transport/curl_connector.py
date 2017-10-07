import platform
import pycurl
import curl_codes
from io import BytesIO
from StringIO import StringIO
from contextlib import contextmanager

from src.logger import get_logger
from .exceptions import ECurlUndefinedAttribute
from .exceptions import ECurlUndefinedMethod
from .exceptions import ECurlStatusLineExpected
from .exceptions import ECurlConnectionTimeout
from .exceptions import ECurlDownloadLimitExceeded
from .exceptions import ECurlProxyError
from .exceptions import ECurlUnknownRequestError
from .exceptions import ECurlMethodRequestError
from .exceptions import ECurlSSLConnectionError
from .exceptions import ECurlConfigError

log = get_logger('core.transport.curl_connector')

if pycurl.version_info()[2] >= 470784:  # hex(470784) => 0x72f00 => 0x07, 0x2f, 0x00 => 7, 47, 0 => 7.47.0
    # log.debug('using custom curl codes')
    codes = curl_codes
else:
    raise Exception('libcurl version must be greater (%s < 7.47.0)' % pycurl.version_info()[1])

UNKNOWN = 0
WINDOWS = 1
LINUX = 2

OS = UNKNOWN
os_name = platform.system().lower()
if os_name.startswith('win'):
    OS = WINDOWS
if os_name.startswith('lin'):
    OS = LINUX

NULL = 'NUL' if OS == WINDOWS else '/dev/null'

log = get_logger('transport')

DEBUG_MODE = 1

PROXY_TYPE_CONNECTOR = {
    'socks4': codes.PROXYTYPE_SOCKS4,
    'socks5': codes.PROXYTYPE_SOCKS5,
    'socks5h': codes.PROXYTYPE_SOCKS5_HOSTNAME,
    'http_no_connect': codes.PROXYTYPE_HTTP,
    'transparent': codes.PROXYTYPE_HTTP,
    'http': codes.PROXYTYPE_HTTP,  # TODO: check if right
    # 'http_1_0': codes.PROXYTYPE_HTTP_1_0,
    # 'socks4a': codes.PROXYTYPE_SOCKS4A,
    # 'socks5_hostname': codes.PROXYTYPE_SOCKS5_HOSTNAME
}

ALLOWED_CIPHERS = [
    'DEFAULT',
    'NULL-MD5',
    'NULL-SHA',
    'RC4-MD5',
    'RC4-SHA',
    'IDEA-CBC-SHA',
    'DES-CBC3-SHA',
    'DH-DSS-DES-CBC3-SHA',
    'DH-RSA-DES-CBC3-SHA',
    'DHE-DSS-DES-CBC3-SHA',
    'DHE-RSA-DES-CBC3-SHA',
    'ADH-RC4-MD5',
    'ADH-DES-CBC3-SHA'
]

_UTF8_TYPES = (bytes, type(None))
BODY_METHODS = ("POST", "PATCH", "PUT")
DEFAULT_STATIC = ['.js', '.pdf']


def utf8(value):
    """Converts a string argument to a byte string.

    If the argument is already a byte string or None, it is returned unchanged.
    Otherwise it must be a unicode string and is encoded as utf8.
    """
    if isinstance(value, _UTF8_TYPES):
        return value
    if not isinstance(value, unicode):
        raise TypeError(
            "Expected bytes, unicode, or None; got %r" % type(value)
        )
    return value.encode("utf-8")


class Response(dict):
    """An object more like email.Message than httplib.HTTPResponse."""

    """Is this response from our local cache"""
    fromcache = False

    """HTTP protocol version used by server. 10 for HTTP/1.0, 11 for HTTP/1.1. """
    version = 11

    "Status code returned by server. "
    status = 200

    """Reason phrase returned by server."""
    reason = "Ok"

    previous = None

    def __init__(self, headers, statusline):
        try:
            self["headers"] = [(i.split(":", 1)[0], i.split(":", 1)[1].strip())
                               for i in headers if ':' in i]  # store headers in self["headers"] instead
        except IndexError as e:
            self["headers"] = [
                (i.split(":", 1)[0], i.split(":", 1)[1].strip()) if len(i.split(":", 1)) > 1 else ('', i.strip())
                for i in headers if ':' in i]  # bad header without ':' sign
        for i in self['headers']:
            self[i[0]] = i[1]

        sl_splitted = statusline.strip().split(' ')
        self.status = int(sl_splitted[1])
        self['status'] = str(sl_splitted[1])
        self.reason = sl_splitted[2:]
        try:
            self.version = int(''.join(sl_splitted[0].split('/')[-1].split('.')))
        except Exception, e:
            self.version = 10

    def __getattr__(self, name):
        if name == 'dict':
            return self
        else:
            raise AttributeError(name)


class Curl(object):
    """ Transport implementation"""

    # _cookie_file = None
    def __init__(self, *args, **kwargs):
        self.h = pycurl.Curl()
        self.write_buffer = None
        self.debug_buffer = None
        self.curl_options = {
            "GET": codes.HTTPGET,
            "POST": codes.POST,
            "PUT": codes.UPLOAD,
            "HEAD": codes.NOBODY,
        }
        self.BODY_METHODS = ('POST',)
        self.ACCEPT_ENCODING_HEADER = 'accept-encoding'
        self.EXPECT_HEADER = 'expect'
        self.CONNECTION_HEADER = 'connection'
        self.SSLv3 = False
        self.http_auth_creds = None
        self.connection_close = False
        self.download_limit = 15728640
        self._error = (None, None)

    def configure(self, download_limit=None, no_body=False,
                  raw_response=False, max_redirects=None, keep_alive=False, timeout=15, expect100_timeout_ms=1000,
                  connect_timeout=5, validate_cert=False, allow_ipv6=True, proxy_info=None, handle_cookie=False,
                  static_files=None, ciper=None, SSLv3=False, http_auth_credintals=None, connection_close=False,
                  cookie_data=None):
        """ Configure transport before sending request
        @param download_limit (int): download limit for pages, in bytes
        @param no_body (bool): get response without body
        @param raw_response (bool): return raw response (with headers in body)
        @param max_redirects (int): count of maximum redirects
        @param keep_alive (bool): sending keep-alive header
        @param timeout (int): timeout for request
        @param expect100_timeout_ms (int): time in ms for waiting for `expect:100` header
        @param connect_timeout (int): timeot for connect
        @param validate_cert (bool): validation of certificate
        @param allow_ipv6 (bool): using ipv6
        @param proxy_info (dict): information for connection via proxy
        @param static_files (tuple): overwrite default extensions for static files
        @param ciper (str): setting ciper for ssl connection
        @param SSLv3 (bool): using SSLv3
        @param http_auth_credintals (list): credintals for http auth
        @param connection_close (bool): sending `connection:close` header
        @return: None

        @raise Exception: timeout or connect_timeout type error
        """
        self.reset()
        self.setopt(codes.NOPROGRESS, 1)
        self.setopt(codes.PATH_AS_IS, 1)
        self.setopt(codes.ACCEPT_ENCODING, '')
        self.setopt(codes.FOLLOWLOCATION, 0)
        self.setopt(codes.MAXREDIRS, max_redirects if max_redirects else -1)
        self.setopt(codes.TCP_KEEPALIVE, keep_alive)
        self.setopt(codes.HEADER, raw_response)

        if not download_limit:
            download_limit = 15728640  # 15 Mb
        if download_limit > 104857600:
            log.warning("Config: download limit exceeded. Limit setted to default value (100 Mb).")
            download_limit = 104857600  # 100 Mb

        self.download_limit = download_limit
        self.setopt(codes.MAXFILESIZE, download_limit)
        self.setopt(codes.PROGRESSFUNCTION, self.progress_handler)
        self.setopt(codes.NOPROGRESS, 0)

        try:
            timeout = int(timeout) if timeout else 15  # or zero?
        except Exception, e:
            raise Exception('Timeout must be int, not %s' % type(timeout))
        self.setopt(codes.TIMEOUT, timeout)

        try:
            connect_timeout = int(connect_timeout) if connect_timeout else 5  # or zero?
        except Exception, e:
            raise Exception('Connect_timeout must be int, not %s' % type(connect_timeout))
        self.setopt(codes.CONNECTTIMEOUT, connect_timeout)

        self.setopt(codes.EXPECT_100_TIMEOUT_MS, expect100_timeout_ms)
        self.setopt(codes.NOBODY, no_body)
        self.connection_close = True if connection_close or raw_response else False

        self._cache.set_static(static_files)

        # libcurl/pycurl is not thread-safe by default.  When multiple threads
        # are used, signals should be disabled.  This has the side effect
        # of disabling DNS timeouts in some environments (when libcurl is
        # not linked against ares), so we don't do it when there is only one
        # thread.
        self.setopt(codes.NOSIGNAL, 1)

        # https://github.com/hwi/HWIOAuthBundle/issues/655
        # Real problem was that CURL (through Buzz) used ipv6 when available.
        # Request on IPV6 address timed out after 5s, a request on an IPV4 address
        # was then done with success. Forcing use of ipv4 would have fix the issue
        # in my particular case. Unfortunately neither HWIOAuthBundle nor Buzz
        # (so far I know) let user set the CURLOPT_IPRESOLVE option to CURL_IPRESOLVE_V4.
        #
        # A solution could be to change internal DNS to bypass IPV6 addresses so we
        # only receive IPV4 but we didn't test it.
        self.setopt(codes.IPRESOLVE, codes.IPRESOLVE_V4)

        if handle_cookie:
            self.setopt(pycurl.COOKIEFILE, "")
        else:
            self.setopt(codes.COOKIEJAR, None)
            self.setopt(codes.COOKIELIST, 'ALL')

        if cookie_data:
            self.setopt(codes.COOKIE, cookie_data)

        if validate_cert:
            self.setopt(codes.SSL_VERIFYPEER, 1)
            self.setopt(codes.SSL_VERIFYHOST, 2)
        else:
            self.setopt(codes.SSL_VERIFYPEER, 0)
            self.setopt(codes.SSL_VERIFYHOST, 0)

        if not allow_ipv6:
            # Curl behaves reasonably when DNS resolution gives an ipv6 address
            # that we can't reach, so allow ipv6 unless the user asks to disable.
            self.setopt(codes.IPRESOLVE, codes.IPRESOLVE_V4)
        else:
            self.setopt(codes.IPRESOLVE, codes.IPRESOLVE_WHATEVER)

        for method in self.curl_options.values():
            self.setopt(method, False)

        if proxy_info:
            # proxy_info.proxy_rdns is not used
            self.setopt(codes.PROXY, proxy_info['host'])
            self.setopt(codes.PROXYTYPE, PROXY_TYPE_CONNECTOR.get(proxy_info['type'], codes.PROXYTYPE_HTTP))
            self.setopt(codes.PROXYPORT, proxy_info['port'])
            if 'user' in proxy_info and 'pass' in proxy_info:
                credentials = '%s:%s' % (proxy_info['user'],
                                         proxy_info['pass'])
                self.setopt(codes.PROXYUSERPWD, credentials)

        if ciper:
            self.setopt(codes.SSL_CIPHER_LIST, ciper)
        else:
            self.setopt(codes.SSL_CIPHER_LIST, None)

        if http_auth_credintals:
            self.add_credentials(**http_auth_credintals)

        self.setopt_credintals()
        self.setopt_SSLv3(SSLv3)

    def setopt_credintals(self):
        """Set credintals"""
        if self.http_auth_creds:
            self.setopt(codes.HTTPAUTH, codes.HTTPAUTH_ANY)
            self.setopt(codes.USERPWD, '%s:%s' % self.http_auth_creds)

    def setopt_SSLv3(self, flag=True):
        self.setopt(codes.SSLVERSION, codes.SSLVERSION_SSLv3 if self.SSLv3 or flag else codes.SSLVERSION_DEFAULT)

    def set_SSLv3(self, turn_on=True):
        self.SSLv3 = turn_on
        self.setopt_SSLv3()

    def add_credentials(self, username, password):
        """ Set credintals for http auth
        @param username (str): username
        @param password (str): password
        @return: None
        """
        self.http_auth_creds = (username, password)
        self.setopt_credintals()

    def clear_credentials(self):
        self.http_auth_creds = None

    def init_storages(self):
        self.write_buffer = StringIO()
        self.debug_buffer = {i: [] for i in xrange(7)}

    def __getattr__(self, item):
        if hasattr(self.h, item):
            return getattr(self.h, item)
        if hasattr(self, item):
            return getattr(self, item)
        raise ECurlUndefinedAttribute(item)

    @contextmanager
    def prepare_to_request(self, url, method='GET', body=None, headers=None, **curlargs):
        """
        @param url (method): url for request
        @param method (str): method
        @param body (str): body
        @param headers (list): additional headers
        @param curlargs (dict): additional params for `configure` method
        @return (None): None

        @raise ECurlUndefinedMethod: method is undefined
        @raise ECurlMethodRequestError: can't set body for this method

        @yield None
        """
        # print '[Curl_] prepare request:', url, method
        # print '[Curl_] cookie before preparing:', self.get_curl_cookies()
        # if headers and 'cookie' in headers:
        #     cstr = headers.pop('cookie')
        #     if isinstance(curlargs['cookie_data'], str):
        #         curlargs['cookie_data'] += '; '+cstr
        if curlargs:
            self.configure(**curlargs)
        # print '[Curl_] cookie after preparing:', self.get_curl_cookies()
        self.init_storages()
        self.setopt(codes.URL, str(url))
        headers_to_curl = ['Expect:']
        if self.connection_close:
            headers_to_curl.append('Connection: Close')
        if headers:
            for i in headers:
                if i.lower() in (self.ACCEPT_ENCODING_HEADER, self.EXPECT_HEADER, self.CONNECTION_HEADER):
                    continue
                headers_to_curl.append("%s: %s" % (i, headers[i]))
        self.setopt(codes.HTTPHEADER, headers_to_curl)
        if method in self.curl_options:
            self.setopt(self.curl_options[method], True)
        else:
            raise ECurlUndefinedMethod(method)
        body_expected = method in BODY_METHODS
        body = str(body) if body is not None else ''
        if body_expected or body:
            if method == 'GET':
                # Even with `allow_nonstandard_methods` we disallow
                # GET with a body (because libcurl doesn't allow it
                # unless we use CUSTOMREQUEST). While the spec doesn't
                # forbid clients from sending a body, it arguably
                # disallows the server from doing anything with them.
                raise ECurlMethodRequestError('Body must be None for GET request')
            request_buffer = BytesIO(utf8(body or ''))

            def ioctl(cmd):
                if cmd == codes.IOCMD_RESTARTREAD:
                    request_buffer.seek(0)

            self.setopt(codes.READFUNCTION, request_buffer.read)
            self.setopt(codes.IOCTLFUNCTION, ioctl)
            if method == "POST":
                self.setopt(codes.POSTFIELDSIZE, len(body or ''))
            else:
                self.setopt(codes.UPLOAD, True)
                self.setopt(codes.INFILESIZE, len(body or ''))

        self.setopt(codes.WRITEDATA, self.write_buffer)
        self.setopt(codes.VERBOSE, 1)
        self.setopt(codes.DEBUGFUNCTION, self.debug_handler)

        yield

        self.setopt(codes.URL, '')
        self.setopt(codes.HTTPHEADER, [])
        self.setopt(codes.VERBOSE, 0)

    def get_last_ip(self):
        """ Get last used ip for connection
        @return (str): ip
        """
        return self.getinfo(codes.PRIMARY_IP)

    def request(self, url, method='GET', body=None, headers=None, **curlargs):
        """ Performing request
        @param url (object with __str__ method): url for request
        @param method (str): method
        @param body (str): body
        @param headers (list): additional headers
        @param curlargs (dict): additional params for `configure` method
        @return response (Response):  response object
        @return resp_body (str): response body
        @return raw_request (str): raw request

        @raise ECurlConnectionTimeout: timeout error
        @raise ECurlDownloadLimitExceeded: download limit exceeded
        @raise ECurlProxyError: proxy error while trying request
        @raise ECurlSSLConnectionError: SSL error while trying request
        @raise ECurlConfigError: URL was not properly formatted
        @raise ECurlUnknownRequestError: unknown curl error
        @raise ECurlStatusLineExpected: no statusline in response
        @raise Shutdown: immediatly shutdown request
        @raise Exception: unknown non-curl error
        """
        response = None
        resp_body = None
        raw_request = None
        # cached = self._cache.get_from_cache(url)
        # if cached:  # remember about basic auth
        #     return cached
        # if get_registry().shutdown_requested:
        #     raise Exception('Raising Shutdown again (probably someone caught and ignored it)') # todo: shutdown!
        with self.prepare_to_request(url, method, body, headers, **curlargs):
            try:
                self.perform()
            except pycurl.error, e:
                effective_url = self.getinfo(codes.EFFECTIVE_URL)

                if self._error[0]:
                    err_code, err_message = self._error
                else:
                    err_code = e[0]
                    err_message = e[1]

                err_str = (effective_url, err_message)

                if err_code == codes.E_OPERATION_TIMEDOUT:
                    raise ECurlConnectionTimeout('Timeout error while trying (%s: %s)' % err_str)
                if err_code == codes.E_FILESIZE_EXCEEDED:
                    raise ECurlDownloadLimitExceeded('Download limit exceeded on %s' % err_str[0])
                if err_code == codes.E_COULDNT_RESOLVE_PROXY:
                    raise ECurlProxyError('Proxy error while trying request (%s: %s)' % err_str)
                if err_code == codes.E_SSL_CONNECT_ERROR:
                    raise ECurlSSLConnectionError('SSL error while trying request (%s: %s)' % err_str)
                if err_code == codes.E_URL_MALFORMAT:
                    raise ECurlConfigError('URL was not properly formatted (%s: %s)' % err_str)
                raise ECurlUnknownRequestError('Unknown error while trying %s: %s' % err_str)
            except Exception, e:
                raise
            # import pprint;  pprint.pprint(self.debug_buffer)
            splitted = self.debug_buffer[1][-1].split('\r\n')
            if ':' in splitted[0]:
                raise ECurlStatusLineExpected()
            response = Response(splitted[1:], splitted[0])
            resp_body = self.write_buffer.getvalue()

            raw_request = self.debug_buffer[codes.INFOTYPE_HEADER_OUT][-1]
            if self.debug_buffer[codes.INFOTYPE_DATA_OUT]:  # append POST data
                raw_request += self.debug_buffer[codes.INFOTYPE_DATA_OUT][-1]

                # self._cache.add_to_cache(url, (response, resp_body, raw_request))
        return response, resp_body

    def get_curl_cookies(self):
        self.setopt(codes.COOKIELIST, 'FLUSH')
        cookie_list = self.getinfo(codes.INFO_COOKIELIST)
        return cookie_list

    def debug_handler(self, code, data):
        """
        @param code (int): code of message type
        @param data (str): message
        @return (None): None
        """
        try:
            if code == 1 and self.debug_buffer[code]:
                if not self.debug_buffer[code][-1].endswith('\r\n\r\n'):
                    self.debug_buffer[code][-1] += data
                    return
            self.debug_buffer[code].append(data)
        except (KeyboardInterrupt, SystemExit):
            pass

    def progress_handler(self, download_total, downloaded, upload_total, uploaded):
        try:
            if self.write_buffer.len > self.download_limit:
                self._error = (codes.E_FILESIZE_EXCEEDED, "")
                return -1
        except KeyboardInterrupt:
            return -1

    def full_info(self):
        return {
            # 'cookie': self.getinfo(codes.COOKIELIST),
            'time': {
                'total-time': self.getinfo(codes.TOTAL_TIME),
                'namelookup-time': self.getinfo(codes.NAMELOOKUP_TIME),
                'pretransfer-time': self.getinfo(codes.PRETRANSFER_TIME),
                'starttransfer-time': self.getinfo(codes.STARTTRANSFER_TIME),
                'redirect-time': self.getinfo(codes.REDIRECT_TIME),
                'filetime': self.getinfo(codes.INFO_FILETIME),
                'connect-time': self.getinfo(codes.CONNECT_TIME),
            },
            'effective-url': self.getinfo(codes.EFFECTIVE_URL),
            'http-code': self.getinfo(codes.HTTP_CODE),
            'size-upload': self.getinfo(codes.SIZE_UPLOAD),
            'size-download': self.getinfo(codes.SIZE_DOWNLOAD),
            'speed-upload': self.getinfo(codes.SPEED_UPLOAD),
            'header-size': self.getinfo(codes.HEADER_SIZE),
            'request-size': self.getinfo(codes.REQUEST_SIZE),
            'content-length-download': self.getinfo(codes.CONTENT_LENGTH_DOWNLOAD),
            'content-length-upload': self.getinfo(codes.CONTENT_LENGTH_UPLOAD),
            'content-type': self.getinfo(codes.CONTENT_TYPE),
            'response-code': self.getinfo(codes.RESPONSE_CODE),
            'speed-download': self.getinfo(codes.SPEED_DOWNLOAD),
            'ssl-verifyresult': self.getinfo(codes.SSL_VERIFYRESULT),
            'redirect-count': self.getinfo(codes.REDIRECT_COUNT),
            'http-connectcode': self.getinfo(codes.HTTP_CONNECTCODE),
            'httpauth-avail': self.getinfo(codes.HTTPAUTH_AVAIL),
            'proxyauth-avail': self.getinfo(codes.PROXYAUTH_AVAIL),
            'os-errno': self.getinfo(codes.OS_ERRNO),
            'num-connects': self.getinfo(codes.NUM_CONNECTS),
            'ssl-engines': self.getinfo(codes.SSL_ENGINES),
            'cookielist': self.getinfo(codes.INFO_COOKIELIST),
            'lastsocket': self.getinfo(codes.LASTSOCKET),
            'ftp-entry-path': self.getinfo(codes.FTP_ENTRY_PATH),
        }

    def __del__(self):
        self.h.close()
