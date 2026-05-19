class AppException(Exception):
    def __init__(self, message: str, error_code: str, status_code: int = 400):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code


class AuthException(AppException):
    pass


class RBACException(AppException):
    pass


class PIIException(AppException):
    pass


class RateLimitException(AppException):
    pass


class DBException(AppException):
    pass