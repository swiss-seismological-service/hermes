import json
import urllib2


class Client:
    def __init__(self, url):
        self.url = url

    def get_events(self, starttime=None, endtime=None):
        url = self.url
        starttime = starttime.strftime('%Y-%m-%dT%H:%M:%S')
        endtime = endtime.strftime('%Y-%m-%dT%H:%M:%S')
        args = []
        if starttime:
            args.append('starttime=' + starttime)
        if endtime:
            args.append('endtime=' + endtime)
        if args:
            url += '?' + '&'.join(args)

        result = urllib2.urlopen(url)
        code = result.getcode()
        if code == 204:
            raise HYDWSException('No data available for request.')
        elif code == 400:
            raise HYDWSException('Bad request. Please contact the developers.')
        elif code == 401:
            raise HYDWSException('Unauthorized, authentication required.')
        elif code == 403:
            raise HYDWSException('Authentication failed.')
        elif code == 413:
            raise HYDWSException('Request would result in too much data. '
                                 'Denied by the datacenter. Split the request '
                                 'in smaller parts.')

        catalog = json.load(result)
        return catalog


class HYDWSException(Exception):
    def __init__(self, *args):
        Exception.__init__(self, *args)
