# -*- coding: utf-8 -*-

import requests
import datetime
import json
from lxml import html

import sys
if (sys.version).startswith('2'):
    reload(sys)
    sys.setdefaultencoding('utf-8')


CPSK_URL = 'http://cp.hnonline.sk/{0}/spojenie/'


class Line(object):
    def __init__(self):
        self.f = ''
        self.t = ''
        self.departure = ''
        self.arrival = ''
        self.vehicle = ''
        self.walk_duration = ''
        self.delay = ''
        self.link_number = ''
        self.date = ''

    def __repr__(self):
        if self.vehicle == 'Presun':
            return u'{0}-> {1}{2}'.format(self.f, self.t, self.walk_duration)
        return u'[{0}]{1} {2} {3} -> {4} {5}{6}'.format(self.vehicle,
                                                        self.link_number,
                                                        self.f,
                                                        self.departure,
                                                        self.t,
                                                        self.arrival,
                                                        self.delay)

    def json(self):
        if self.vehicle == 'Presun':
            result = {
                "from": self.f.strip(),
                "to": self.t.strip(),
                "walkDuration": self.walk_duration.strip()
            }

            return json.dumps(result)

        result = {
            "vehicle": 'TRAM' if self.vehicle == 'Električka' else 'BUS',
            "linkNumber": self.link_number.strip(),
            "from": self.f.strip(),
            "to": self.t.strip(),
            "departure": self.departure.strip(),
            "arrival": self.arrival.strip(),
            "delay": self.delay.strip()
        }
        
        return json.dumps(result)


class Drive(object):
    def __init__(self):
        self.duration = None
        self.distance = None

        self.lines = []

    def __repr__(self):
        return '{0} ({1}, {2})'.format(' >> '.join(map(str, self.lines)), self.duration, self.distance)

    def json(self):
        result = {
            "lines": map(lambda line: line.json(), self.lines),
            "duration": self.duration.strip(),
            "distance": self.distance.strip()
        }

        return json.dumps(result)


def get_routes(departure, dest, vehicle='vlakbus', time='', date=''):
    """Return list of available routes from departure city to destination"""

    def _get_leaf_element(table, path):
        """Returns leaf element's text in given path"""
        res = table.xpath(path + '/*[not(*)]')
        if res:
            return res[0].text
        return table.xpath(path + '/text()')[0]

    if time == '':
        time = datetime.datetime.now().strftime('%H:%M')

    if date == '':
        date = datetime.datetime.now().strftime('%d.%m.%Y')

    try:
        req = requests.get(CPSK_URL.format(vehicle),
                           params={'date': date, 'time': time, 'f': departure,
                                   't': dest, 'submit': 'true'})
    except:
        return False

    tree = html.fromstring(req.text)
    html_tables = tree.xpath('//div[@id="main-res-inner"]/table/tbody')
    routes = []

    for table in html_tables:
        drive = Drive()
        datalen = len(table.xpath('./tr'))

        prevdate = ''
        for i in range(1, datalen-1):
            line = Line()
            trf = './tr[' + str(i) + ']'
            trt = './tr[' + str(i+1) + ']'
            line.f = _get_leaf_element(table, trf + '/td[3]')
            line.t = _get_leaf_element(table, trt + '/td[3]')
            line.departure = _get_leaf_element(table, trf + '/td[5]')
            line.arrival = _get_leaf_element(table, trt + '/td[4]')
            line.vehicle = table.xpath(trf + '/td[7]/img[1]')[0] \
                                .get('title').replace('Autobus', 'Bus')
            if line.vehicle == 'Presun':
                line.walk_duration = table.xpath(trf + '/td[7]/text()')[0] \
                                        .replace('Presun asi ', '')

            delay = table.xpath(trf + '/td[7]/div[1]/' +
                                'span[@class!="nodelay"]/text()')
            if delay and delay[0] is not u'Aktuálne bez meškania':
                mins = delay[0].replace(u'Aktuálne meškanie ', '') \
                               .replace(u' minúty', '') \
                               .replace(u' minútu', '') \
                               .replace(u' minút', '')

                minstr = 'minutes' if mins is not '1' else 'minute'

                line.delay = ' ({0} {1} delay)'.format(mins, minstr)
                
            link_number = table.xpath(trf + '/td[last()]')[0].text_content()

            if link_number:
                line.link_number = link_number

            _date = table.xpath(trf + '/td[2]/text()')[0]
            if _date is not ' ':
                prevdate = _date
            line.date = prevdate

            drive.lines.append(line)

        drive.duration = table.xpath('./tr[' + str(datalen) + ']/td[3]/p/strong[1]/text()')[0]

        try:
            drive.distance = table.xpath('./tr[' + str(datalen) + ']/td[3]/p/strong[2]/text()')[0]

            if 'EUR' in drive.distance:
                drive.distance = ''

        except IndexError:
            drive.distance = 'Distance unknown'

        routes.append(drive.json())

    return routes
