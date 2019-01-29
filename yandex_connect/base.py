# coding: utf8

"""
Yandex.Connect Base API module
:author: Alexeev Nick
:email: n@akolka.ru
:version: 0.01b
"""

import json
import requests
import datetime
import inspect


def token_get_by_code():
    import requests
    print ('Attempt to get oauth token for app')
    client_id = input('Client id: ')
    client_secret = input('Client secret: ')
    print ('Open link in browser:')
    print ('https://oauth.yandex.ru/authorize?response_type=code&client_id=%s' % client_id)
    code = input('Enter code: ')

    auth = '%s:%s' % (client_id, client_secret)
    headers = {
        "Authorization": "Basic %s" % auth.encode('base64').replace('\n', '').strip()
    }
    r = requests.post(
        'https://oauth.yandex.ru/token',
        headers=headers,
        data={
            'grant_type': 'authorization_code',
            'code': code
        }
    )
    print (r.text)


def json_prepare_dump(obj):
    """
    Подготовка к json.dumps
    :param obj: объект
    :return: подготовленный объект
    """
    if isinstance(obj, list):
        for i, item in enumerate(obj):
            obj[i] = json_prepare_dump(item)
    elif isinstance(obj, dict):
        for key in obj:
            obj[key] = json_prepare_dump(obj[key])
    elif type(obj) is datetime.date:
        return obj.isoformat()
    elif isinstance(obj, datetime.datetime):
        return obj.isoformat()
    return obj


def inspect_args_func(frame):
    """
    Inspect current def arguments
    :param frame: inspect.currentframe()
    :return: dict
    """
    args, _, _, values = inspect.getargvalues(frame)
    return {key: values[key] for key in args if key != 'self'}


class YandexConnectException(Exception):
    """
    Exception of module
    """
    pass


class YandexConnectExceptionY(Exception):
    """
    Exception by yandex request
    """
    pass


class YandexConnectRequest(object):
    """ Yandex Connect request API object """

    _version = None  # API version
    _oauth_token = None  # OAuth Token
    _org_id = None  # Org ID
    _domain = None  # Domain

    def __init__(self, domain, oauth_token, org_id=None, version=6):
        """
        Init
        :param domain: yandex domain
        :param oauth_token: OAuth Token — https://oauth.yandex.ru/
        :param org_id: Organization id
        :param version: API version
        """
        self._domain = domain
        self._oauth_token = oauth_token
        self._org_id = org_id
        if version:
            self._version = version

    def __call__(self, name, data=None, method='post'):
        """
        Base request method
        :param name: url path
        :param data: data / args of request
        :param method: request method - get/post
        :raise YandexConnectException: bad request, jsonify failed
        :raise YandexConnectExceptionY: yandex exception
        :return: dict
        """
        url = '%(domain)s/v%(version)s/%(name)s' % {
            'domain': self._domain,
            'version': self._version,
            'name': name
        }
        if not url.endswith('/'):
            url = '%s/' % url

        if data:
            for key in list(data):
                if data[key] is None or (isinstance(data[key], dict) and not data[key]):
                    del data[key]
                    continue
        method = method.lower()
        if method not in ['get', 'post', 'patch', 'delete']:
            raise ValueError('Not right method')
        kwargs = {
            'headers': {
                'Authorization': 'OAuth %s' % self._oauth_token,
                'X-Org-ID': str(self._org_id) if self._org_id else None
            }
        }
        if method in ['post', 'patch']:
            if data:
                module = name.split('/')[0]
                if module.endswith('s'):
                    module = module[:-1]
                key_id = '%s_id' % module
                if key_id in data:
                    del data[key_id]
                kwargs['data'] = json.dumps(json_prepare_dump(data))
                kwargs['headers']['Content-Type'] = 'application/json'
        else:
            kwargs['params'] = data

        if not kwargs['headers']['X-Org-ID']:
            del kwargs['headers']['X-Org-ID']

        try:
            r = getattr(requests, method)(url, **kwargs)
        except Exception:
            raise YandexConnectException(u'Request error: send', name, data)
        if r.status_code > 299:
            try:
                msg = r.json()
            except Exception:
                msg = r.text
            raise YandexConnectExceptionY(r.status_code, msg, url, kwargs)
        if method == 'delete':
            return True
        try:
            ret = r.json()
        except Exception:
            return True
        return ret


class YandexConnectBase(object):
    """ Yandex connect API base class"""

    DOMAIN = None  # Request Domain

    request = None  # Request object

    def __init__(self, oauth_token, org_id=None, version=6):
        """
        :param oauth_token: OAuth token
        :param org_id: ID org
        :param version: API version
        """
        self.request = YandexConnectRequest(self.DOMAIN, oauth_token, org_id=org_id, version=version)

    @staticmethod
    def prepare_fields(fields, title_field, only_title_field=False):
        """
        Prepare fields data key
        :param fields: obj
        :param title_field: second field
        :param only_title_field: return only title field
        :return:
        """
        if not fields:
            if not only_title_field:
                fields = ['id', title_field]
            else:
                fields = [title_field]
        if isinstance(fields, list):
            fields = u','.join(fields)
        return fields

    def list_full(self, callback, default_field, **kwargs):
        """
        List full
        :param callback: callback function
        :param default_field: default field
        :param kwargs: params
        :return: list
        """
        kwargs['fields'] = self.prepare_fields(kwargs.get('fields'), default_field)
        kwargs['per_page'] = 100
        pages = None
        page = 1
        ret = []
        while True:
            kwargs['page'] = page
            r = callback(**kwargs)
            if pages is None:
                pages = r['pages']
            ret += r['result']
            if page >= pages:
                break
            page += 1
        return ret
