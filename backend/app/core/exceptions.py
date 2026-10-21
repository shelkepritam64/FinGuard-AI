class FinGuardError(Exception):
    """Base exception for FinGuard AI backend."""
    pass


class ModelNotFoundError(FinGuardError):
    """Raised when a requested model ID is not registered."""
    pass


class ModelUnavailableError(FinGuardError):
    """Raised when a requested model is registered but marked unavailable."""
    pass


class ArtifactMissingError(FinGuardError):
    """Raised when an expected artifact file does not exist on disk."""
    pass


class PreprocessingError(FinGuardError):
    """Raised when input validation, feature missing, or encoding fails."""
    pass


class InferenceError(FinGuardError):
    """Raised when model inference execution encounters an error."""
    pass
