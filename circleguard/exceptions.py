class CircleguardException(Exception):
    """Base class for exceptions in the circleguard program."""

class InvalidArgumentsException(CircleguardException):
    """Indicates an invalid argument was passed to one of the flags."""

class APIException(CircleguardException):
    """
    Indicates an error involving the API, which may or may not be fatal.

    UnknownAPIExceptions are considered fatal, InternalAPIExceptions are not.
    """

class UnknownAPIException(APIException):
    """Indicates some error on the API's end that we were not prepared to handle."""

class InternalAPIException(APIException):
    """Indicates a response from the API that we know how to handle."""

class InvalidKeyException(InternalAPIException):
    """Indicates that the given api key was rejected by the api."""

class RatelimitException(InternalAPIException):
    """Indicates that our key has been ratelimited and we should retry the request at a later date."""

class ReplayUnavailableException(InternalAPIException):
    """Indicates that we expected a replay from the api but it was not able to deliver it."""
