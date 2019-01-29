#!/usr/bin/env python
# -*- coding: utf-8 -*-

import abc
import json
import datetime
import logging
import hashlib
import uuid
from optparse import OptionParser
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
import scoring


SALT = "Otus"
ADMIN_LOGIN = "admin"
ADMIN_SALT = "42"
OK = 200
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
INVALID_REQUEST = 422
INTERNAL_ERROR = 500
ERRORS = {
    BAD_REQUEST: "Bad Request",
    FORBIDDEN: "Forbidden",
    NOT_FOUND: "Not Found",
    INVALID_REQUEST: "Invalid Request",
    INTERNAL_ERROR: "Internal Server Error",
}
UNKNOWN = 0
MALE = 1
FEMALE = 2
GENDERS = {
    UNKNOWN: "unknown",
    MALE: "male",
    FEMALE: "female",
}
NOT_VALID = 'not_valid'


class Field(object):
    def __init__(self, value=None, required=False, nullable=True):
        self.value = value
        self.required = required
        self.nullable = nullable

    def __get__(self, instance, value):
        return self.value

    def __set__(self, instance, value):
        self.value = value
        if self.required and self.value is None:
            self.value = NOT_VALID
        if not self.nullable and len(self.value) == 0:
            self.value = NOT_VALID
        self._validate()

    def _validate(self):pass


class CharField(Field):
    def _validate(self):
        if self.value is None:
            return
        if not isinstance(self.value, str) and not isinstance(self.value, unicode):
            self.value = NOT_VALID


class ArgumentsField(Field):
    def _validate(self):
        if self.value and not isinstance(self.value, dict):
            self.value = NOT_VALID


class EmailField(CharField):
    def _validate(self):
        if self.value is None:
            return
        if self.value.find("@") == -1:
            self.value = NOT_VALID


class PhoneField(Field):
    def __init__(self, phone_len=11, value=None, required=False, nullable=True):
        super(PhoneField, self).__init__(value)
        self.phone_len = phone_len

    def _validate(self):
        if self.value is None:
            return
        if not (isinstance(self.value, str) or isinstance(self.value, int)):
            self.value = NOT_VALID
        if len(str(self.value)) != self.phone_len:
            self.value = NOT_VALID
        if not str(self.value).startswith('7'):
            self.value = NOT_VALID


class DateField(Field):
    def _validate(self):
        if self.value is None:
            return
        try:
            self.date = datetime.datetime.strptime(self.value, "%d.%m.%Y").date()
        except ValueError:
            self.value = NOT_VALID


class BirthDayField(DateField):
    def _validate(self):
        if self.value is None:
            return
        try:
            self.date = datetime.datetime.strptime(self.value, "%d.%m.%Y").date()
        except ValueError:
            self.value = NOT_VALID
        current_year = datetime.date.today().year
        if (current_year - self.date.year) < 0:
            self.value = NOT_VALID
        if (current_year - self.date.year) > 70:
            self.value = NOT_VALID


class GenderField(Field):
    def _validate(self):
        if self.value is None:
            return
        if self.value not in (0, 1, 2):
            self.value = NOT_VALID


class ClientIDsField(Field):
    def _validate(self):
        if not self.value:
            self.value = NOT_VALID
        if not isinstance(self.value, list):
            self.value = NOT_VALID
        for item in self.value:
            if not isinstance(item, int):
                self.value = NOT_VALID


class RequestMeta(type):
    def __new__(self, name, bases, attrs):
        fields = []
        for key, val in attrs.iteritems():
            if isinstance(val, Field):
                fields.append(key)

        cls = super(RequestMeta, self).__new__(self, name, bases, attrs)
        cls._fields = fields
        return cls


class RequestBase(object):
    __metaclass__ = RequestMeta

    def __init__(self, data):
        if not isinstance(data, dict):
            self.data = {}
        else:
            self.data = data

        for key, val in self.data.iteritems():
            setattr(self, key, val)

    @property
    def request_dict(self):
        validating_request = {}
        for key in dir(self):
            if key in self._fields:
                validating_request[key] = getattr(self, key)
        return validating_request

    @property
    def is_valid(self):
        for key, val in self.request_dict.items():
            if val == NOT_VALID:
                return False
        return True


class ClientsInterestsRequest(RequestBase):
    def __init__(self, data):
        self.client_ids = None
        self.date = None
        super(ClientsInterestsRequest, self).__init__(data)

    client_ids = ClientIDsField(required=True)
    date = DateField(required=False, nullable=True)

    @property
    def get_response(self):
        response = {}
        if not self.is_valid:
            response = {'error': []}
            for key, val in self.request_dict.items():
                if val == NOT_VALID:
                    response['error'] += key
            code = INVALID_REQUEST
        else:
            for id in self.client_ids:
                response[id] = scoring.get_interests(None, id)
            code = OK

        return response, code


class OnlineScoreRequest(RequestBase):
    def __init__(self, data):
        self.first_name = None
        self.last_name = None
        self.email = None
        self.phone = None
        self.birthday = None
        self.gender = None
        super(OnlineScoreRequest, self).__init__(data)

    first_name = CharField(required=False, nullable=True)
    last_name = CharField(required=False, nullable=True)
    email = EmailField(required=False, nullable=True)
    phone = PhoneField(required=False, nullable=True)
    birthday = BirthDayField(required=False, nullable=True)
    gender = GenderField(required=False, nullable=True)

    @property
    def is_valid(self):
        for key, val in self.request_dict.items():
            if val == NOT_VALID:
                return False
        if self.email is None or self.phone is None:
            if self.birthday is None or self.gender is None:
                if self.first_name is None or self.last_name is None:
                    return False
        return True

    @property
    def get_response(self):
        response = {}
        if not self.is_valid:
            response = {'error':[]}
            for key, val in self.request_dict.items():
                if val == NOT_VALID:
                    response['error'] += [key]
            code = INVALID_REQUEST
        else:
            response['score'] = scoring.get_score(None, self.phone, self.email, self.birthday, self.gender,
                                                  self.first_name, self.last_name)
            code = OK

        return response, code


class MethodRequest(RequestBase):
    def __init__(self, data):
        self.account = ''
        self.login = ''
        self.token = None
        self.arguments = None
        self.method = None
        super(MethodRequest, self).__init__(data)

    account = CharField(required=False, nullable=True)
    login = CharField(required=True, nullable=True)
    token = CharField(required=True, nullable=True)
    arguments = ArgumentsField(required=True, nullable=True)
    method = CharField(required=True, nullable=False)

    @property
    def is_admin(self):
        return self.login == ADMIN_LOGIN


def check_auth(request):
    if request.is_admin:
        digest = hashlib.sha512(datetime.datetime.now().strftime("%Y%m%d%H") + ADMIN_SALT).hexdigest()
    else:
        digest = hashlib.sha512(request.account + request.login + SALT).hexdigest()
    if digest == request.token:
        return True
    return False


def method_handler(request, ctx, store):
    response, code = None, None
    if not request["body"]:
        return ERRORS[INVALID_REQUEST], INVALID_REQUEST

    processed_request = MethodRequest(request["body"])

    if not processed_request.request_dict:
        return ERRORS[INVALID_REQUEST], INVALID_REQUEST

    if not check_auth(processed_request):
        return ERRORS[FORBIDDEN], FORBIDDEN

    if processed_request.method == 'online_score':
        try:
            ctx['has'] = []
            for key, val in processed_request.arguments.items():
                if not val is None or val != '':
                    ctx['has'] += [key]
        except:
            ctx['has'] = []

        if processed_request.is_admin:
            return {"score": 42}, OK

        if not processed_request.arguments:
            return ERRORS[INVALID_REQUEST], INVALID_REQUEST
        else:
            response, code = OnlineScoreRequest(processed_request.arguments).get_response

    elif processed_request.method == 'clients_interests':

        if not processed_request.arguments:
            return ERRORS[INVALID_REQUEST], INVALID_REQUEST
        else:
            try:
                ctx['nclients'] = len(processed_request.arguments['client_ids'])
            except:
                ctx['nclients'] = 0

            response, code = ClientsInterestsRequest(processed_request.arguments).get_response
    else:
        return ERRORS[INVALID_REQUEST], INVALID_REQUEST

    return response, code


class MainHTTPHandler(BaseHTTPRequestHandler):
    router = {
        "method": method_handler
    }
    store = None

    def get_request_id(self, headers):
        return headers.get('HTTP_X_REQUEST_ID', uuid.uuid4().hex)

    def do_POST(self):
        response, code = {}, OK
        context = {"request_id": self.get_request_id(self.headers)}

        request = None
        try:
            data_string = self.rfile.read(int(self.headers['Content-Length']))
            request = json.loads(data_string)
        except:
            code = BAD_REQUEST

        if request:
            path = self.path.strip("/")
            logging.info("%s: %s %s" % (self.path, data_string, context["request_id"]))
            if path in self.router:
                try:
                    response, code = self.router[path]({"body": request, "headers": self.headers}, context, self.store)
                except Exception, e:
                    logging.exception("Unexpected error: %s" % e)
                    code = INTERNAL_ERROR
            else:
                code = NOT_FOUND

        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if code not in ERRORS:
            r = {"response": response, "code": code}
        else:
            r = {"error": response or ERRORS.get(code, "Unknown Error"), "code": code}
        context.update(r)
        logging.info(context)
        self.wfile.write(json.dumps(r))
        return


if __name__ == "__main__":
    op = OptionParser()
    op.add_option("-p", "--port", action="store", type=int, default=8080)
    op.add_option("-l", "--log", action="store", default=None)
    (opts, args) = op.parse_args()
    logging.basicConfig(filename=opts.log, level=logging.INFO,
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    server = HTTPServer(("localhost", opts.port), MainHTTPHandler)
    logging.info("Starting server at %s" % opts.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
