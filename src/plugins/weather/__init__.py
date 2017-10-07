# -*- coding:utf-8 -*-
import json

from copy import copy
from src.transport import get_transport


class Weather(object):
    def __init__(self, config):
        self._transport = get_transport()
        self.appid = config.openweathermap_appid
        self._urls = {
            'now': "http://api.openweathermap.org/data/2.5/weather?",
            'future_1': "http://api.openweathermap.org/data/2.5/forecast?",
        }
        self._default_args = {
            'q': config.default_city,
            'APPID': config.openweathermap_appid,
            'lang': "ru",
            'units': "metric",
        }
        self._answer_template = {
            'now': u"""Сейчас на улице {description}, {temp} градусов по Цельсию""",
            'future_1': u"""Завтра на улице {description}, {temp} градусов по Цельсию""",
        }

    def check_message(self, message):
        code = None
        city = None
        if not any(word in message for word in [u'погод', u'за окном']):
            return None, None
        code = 'now'
        if any(word in message for word in [u'сегодня', u'сейчас']):
            code = 'now'
        elif any(word in message for word in [u'завтра', ]):
            code = 'future_1'
        city_flags = [u' в городе ', u'г.']
        for flag in city_flags:
            if flag in message:
                city = message.split(flag)[-1].strip().encode('utf-8')
                break
        return code, city

    def process_message(self, message):
        code, city = self.check_message(message.msg)
        if code is None:
            return None
        return self.get_weather(city=city, date=code)

    def _prepare_url(self, city, date='now'):
        current_args = copy(self._default_args)
        if city is not None:
            current_args['q'] = city
        if any(map(lambda x: x is None, current_args.itervalues())):
            return None
        current_args = {i: str(j) for i, j in current_args.iteritems()}
        params = '&'.join(map('='.join, current_args.iteritems()))
        _url = self._urls.get(date)
        if not _url:
            return None
        url = _url + params
        return url

    def _prepare_answer(self, response_data, date):
        # import pprint
        # pprint.pprint(response_data)
        # print(response_data)
        # print type(response_data)
        params = {
            'description': response_data['weather'][0]['description'],
            'temp': int(response_data['main']['temp'])
        }
        tmpl = self._answer_template.get(date)
        if not tmpl:
            return None
        return tmpl.format(**params)

    def get_weather(self, city=None, date='now'):
        url = self._prepare_url(city=city, date=date)
        if not url:
            return 'Sorry, we cant prepare request to weather aggregator'
        response, resp_body = self._transport.request(url)
        response_data = json.loads(resp_body)
        if response.status != 200:
            print response_data
            return response_data.get("message") or 'Unknown error'
        answer = self._prepare_answer(response_data, date)
        return answer or 'Sorry, we cant understand answer from weather aggregator'


if __name__ == "__main__":
    # class Config:
    #     default_city = "Moscow"
    #     openweathermap_appid = "817655035f8dcf97d19ba799cd3098c7"
    # class Message:
    #     msg = 'text'
    #     msg = 'погода завтра'
    # w = Weather(Config())
    # print w.process_message(Message())
    resp, body = get_transport().request('https://iambrave.dctf-quals-17.def.camp/')
    print resp
    print '-' * 10
    print body
