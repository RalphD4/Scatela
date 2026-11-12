class ServiceError(Exception):
    """Base exception for service-layer domain and validation errors."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class ValidationError(ServiceError):
    def __init__(self, message: str):
        super().__init__(message, status_code=400)


class AuthenticationError(ServiceError):
    def __init__(self, message: str = "Invalid credentials"):
        super().__init__(message, status_code=401)


class AuthorizationError(ServiceError):
    def __init__(self, message: str = "You are not authorized to access this resource"):
        super().__init__(message, status_code=403)


class NotFoundError(ServiceError):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class ConflictError(ServiceError):
    def __init__(self, message: str = "Resource already exists"):
        super().__init__(message, status_code=409)
