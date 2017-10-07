# -*- coding:utf-8 -*-

'''
Here are defined all exceptions that are raised by RequestContext during performing a http request.
This exceptions are simple wrappers for different ErrorReponses.
curlconnector catches only this exceptions (actually only their base - RequestError) and gets corresponding ErrorResponse.
'''


class BaseResponse(object):
    """Base class for all responses"""
    pass


class ErrorResponse(BaseResponse):
    """Base class for all error responses"""

    UNKNOWN = 1
    CONNECT_FAIL = 2
    TIMEOUT = 3
    FILTERED = 4
    DOWNLOAD_LIMIT_EXCEEDED = 5
    PROXY_FAIL = 6
    REDIRECT_COUNT_EXCEEDED = 7
    MISSING_LOCATION_HEADER = 8
    REDIRECT_FAILED = 9

    def __init__(self, error_code, error_descr, request):
        """
        @param error_code (int) - one of the class-level constants
        @param error_descr (str) - error description
        @param request (BaseRequest) - request for this response
        """

        self.error = int(error_code)
        self.error_descr = str(error_descr)
        self.request = request

    def __repr__(self):
        return "<ErrorResponse code=%d descr=%s>" % (self.error, self.error_descr)


class RequestError(Exception):
    '''Virtual class for request exceptions'''

    code = None  # for inherited classes

    def __init__(self, message, request):
        # must get code from inherited class
        assert self.code is not None

        self.message = message
        # TODO: we can cache error responses in local registry
        # may be worth it only if most error messages
        # are the same for each ErrorResponse type
        self.response = ErrorResponse(self.code, self.message, request)

    def __str__(self):
        return self.message


class UnknownRequestError(RequestError):
    code = ErrorResponse.UNKNOWN


class ConnectionFailed(RequestError):
    code = ErrorResponse.CONNECT_FAIL


class ConnectionTimeout(RequestError):
    code = ErrorResponse.TIMEOUT


class RequestFiltered(RequestError):
    code = ErrorResponse.FILTERED


class RedirectFiltered(RequestError):
    code = ErrorResponse.FILTERED


class DownloadLimitExceeded(RequestError):
    code = ErrorResponse.DOWNLOAD_LIMIT_EXCEEDED


class ProxyError(RequestError):
    code = ErrorResponse.PROXY_FAIL


class MissingLocation(RequestError):
    code = ErrorResponse.MISSING_LOCATION_HEADER


class RedirectLimitExceeded(RequestError):
    code = ErrorResponse.REDIRECT_COUNT_EXCEEDED


class RedirectFailed(RequestError):
    code = ErrorResponse.REDIRECT_FAILED


# CurlExceptions
class BaseCurlException(Exception):
    pass


class ECurlUndefinedAttribute(BaseCurlException):
    pass


class ECurlUndefinedMethod(BaseCurlException):
    pass


class ECurlStatusLineExpected(BaseCurlException):
    pass


class ECurlConnectionTimeout(BaseCurlException):
    pass


class ECurlDownloadLimitExceeded(BaseCurlException):
    pass


class ECurlProxyError(BaseCurlException):
    pass


class ECurlUnknownRequestError(BaseCurlException):
    pass


class ECurlMethodRequestError(BaseCurlException):
    pass


class ECurlSSLConnectionError(BaseCurlException):
    pass


class ECurlConfigError(BaseCurlException):
    pass
