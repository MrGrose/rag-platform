class DomainError(Exception):
    pass


class NotFoundError(DomainError):
    pass


class ConflictError(DomainError):
    pass


class ValidationError(DomainError):
    pass


class ServiceUnavailableError(DomainError):
    pass


class ConfigurationError(DomainError):
    pass
