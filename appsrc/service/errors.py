
class ServiceError(BaseException):
    code = 400
    message = 'Unspecified error'

    def __init__(self, code=None, message=None):
        super().__init__()
        if code is not None:
            self.code = code
        if message is not None:
            self.message = message


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
