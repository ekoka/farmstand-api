
def _wrong_type_err(name, value, expected_type):
    err = (f'Wrong type for ServiceError {name}: expected {expected_type.__name__} '
    'got {type(value).__name__} instead')
    return TypeError(err)


class ServiceError(BaseException):
    code = 400
    message = 'Unspecified error'

    def __init__(self, code=None, message=None):
        """
        ServiceError can be created with only code or only message.
        Constructor assigns int to code and str to message.
        Error is raise with ambiguous input.
        """
        super().__init__()
        if code is not None:
            def _assign_code():
                _type = type(code)
                if _type is  int:
                    self.code = code
                    return
                if _type is str and message is None:
                    # The code was meant as the message
                    self.message = code
                    return
                raise _wrong_type_err('code', _type, int)
            _assign_code()
        if message is not None:
            def _assign_message():
                _type = type(message)
                if _type is str:
                    self.message = message
                    return
                if _type is int and code is None:
                    # The message was meant as the code
                    self.code = message
                    return
                raise _wrong_type_err('message', _type, str)
            _assign_message()

class FormatError(ServiceError):
    code = 400
    message = 'Format error'

class NotAuthenticated(ServiceError):
    code = 401
    message = 'Not authenticated'

class NotAuthorized(ServiceError):
    code = 403
    message = 'Not authorized'

class NotFound(ServiceError):
    code = 404
    message = 'Resource not found'

class ActionNotAllowed(ServiceError):
    code = 405
    message = 'Action not allowed'

class Conflict(ServiceError):
    code = 409
    message = 'Conflict'

to_dict = lambda error: {"code": error.code or "", "message": error.message or ""}
