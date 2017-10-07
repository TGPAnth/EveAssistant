import json

import xmltodict
import yaml
from yaml.error import MarkedYAMLError

from .error import ConfigFormatError


class Reader(object):
    @classmethod
    def from_file(cls, filepath):
        raise NotImplemented()


class YamlReader(Reader):
    @classmethod
    def from_file(cls, filepath):
        try:
            with open(filepath) as f:
                return yaml.safe_load(f)
        except MarkedYAMLError as e:
            raise ConfigFormatError(e)


class XmlReader(Reader):
    @classmethod
    def from_file(cls, filepath):
        try:
            with open(filepath) as f:
                data = xmltodict.parse(f)

                return cls._prepare_dict(data['config'])
        except Exception as e:
            raise ConfigFormatError(e)

    @classmethod
    def _prepare_dict(cls, data):
        if isinstance(data, dict) and 'list' in data:
            tmp_list = []

            if data['list'] is not None:  # empty list is <list></list>
                if isinstance(data['list']['item'], list):
                    for item in data['list']['item']:
                        if isinstance(item, dict):
                            item = cls._prepare_dict(item)

                        tmp_list.append(item)
                else:
                    tmp_list.append(cls._prepare_dict(data['list']['item']))

            data = tmp_list

        if isinstance(data, dict):
            for key in data:
                if isinstance(data, dict):
                    data[key] = cls._prepare_dict(data[key])

        return data


class JsonReader(Reader):
    @classmethod
    def from_file(cls, file):
        try:
            with open(file) as f:
                data = json.load(f.read())
                return cls._encode(data)
        except ValueError as e:
            raise ConfigFormatError(e)

    @classmethod
    def _encode(cls, data):
        """Encodes all unicode strings as UTF-8 in data returned by json.load"""
        if isinstance(data, dict):
            return {cls._encode(key): cls._encode(value) for key, value in data.iteritems()}
        elif isinstance(data, list):
            return [cls._encode(value) for value in data]
        elif hasattr(data, 'encode'):  # Dirty
            return data.encode('utf-8')
        else:
            return data


readers = {
    'yaml': YamlReader,
    'xml': XmlReader,
    'json': JsonReader
}
