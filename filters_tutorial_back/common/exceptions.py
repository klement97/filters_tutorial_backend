from rest_framework.exceptions import APIException


class InvalidForm(BaseException):
    def __init__(self, form):
        self.form = form

    def to_json(self):
        return self.form.errors.as_json()


class InvalidData(BaseException):

    def __init__(self, message):
        self.message = message

    def get_message(self):
        return self.message


class APIException202(APIException):
    status_code = 202

    def __init__(self, message, obj):
        self.message = message
        self.obj = obj
