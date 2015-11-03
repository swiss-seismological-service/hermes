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

        catalog = json.load(urllib2.urlopen(url))

        return catalog


class HYDWSException(Exception):
    def __init__(self, *args):
        Exception.__init__(self, *args)
