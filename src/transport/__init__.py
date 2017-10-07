from src.transport.curl_connector import Curl

_http = None


def get_transport(name='default'):
    global _http
    if _http is None:
        _http = Curl()
    return _http
