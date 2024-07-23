from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


def add_query_params(url: str, **kwargs) -> str:
    url = urlparse(url)
    url_parts = list(url)
    query = dict(parse_qsl(url_parts[4]))
    query.update(kwargs)
    url = url._replace(query=urlencode(query))
    return urlunparse(url)
