"""Custom exceptions for stackbrew library generation."""

from typing import Optional, Any, Dict


class StackbrewGeneratorError(Exception):
    """Base exception for stackbrew generator errors.

    Provides structured error information with context and suggestions.
    """

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        suggestion: Optional[str] = None,
        original_error: Optional[Exception] = None
    ):
        """Initialize error with context.

        Args:
            message: Error message
            context: Additional context information
            suggestion: Suggested fix or next steps
            original_error: Original exception that caused this error
        """
        super().__init__(message)
        self.context = context or {}
        self.suggestion = suggestion
        self.original_error = original_error

    def get_detailed_message(self) -> str:
        """Get detailed error message with context and suggestions."""
        parts = [str(self)]

        if self.context:
            parts.append("Context:")
            for key, value in self.context.items():
                parts.append(f"  {key}: {value}")

        if self.suggestion:
            parts.append(f"Suggestion: {self.suggestion}")

        if self.original_error:
            parts.append(f"Original error: {self.original_error}")

        return "\n".join(parts)


class GitOperationError(StackbrewGeneratorError):
    """Exception raised for Git operation failures."""

    def __init__(
        self,
        message: str,
        command: Optional[str] = None,
        exit_code: Optional[int] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if command:
            context['command'] = command
        if exit_code is not None:
            context['exit_code'] = exit_code

        suggestion = kwargs.get('suggestion')
        if not suggestion and command:
            if 'ls-remote' in command:
                suggestion = "Check that the remote repository exists and is accessible"
            elif 'fetch' in command:
                suggestion = "Ensure you have network access and proper Git credentials"
            elif 'show' in command:
                suggestion = "Verify that the commit exists and contains the requested file"

        super().__init__(message, context=context, suggestion=suggestion, **kwargs)


class VersionParsingError(StackbrewGeneratorError):
    """Exception raised for version parsing failures."""

    def __init__(self, message: str, version_string: Optional[str] = None, **kwargs):
        context = kwargs.get('context', {})
        if version_string:
            context['version_string'] = version_string

        suggestion = kwargs.get('suggestion',
            "Version should be in format 'X.Y.Z' or 'vX.Y.Z' with optional suffix")

        super().__init__(message, context=context, suggestion=suggestion, **kwargs)


class DistributionError(StackbrewGeneratorError):
    """Exception raised for distribution detection failures."""

    def __init__(
        self,
        message: str,
        dockerfile_path: Optional[str] = None,
        from_line: Optional[str] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if dockerfile_path:
            context['dockerfile_path'] = dockerfile_path
        if from_line:
            context['from_line'] = from_line

        suggestion = kwargs.get('suggestion',
            "Dockerfile should have a FROM line with supported base image (alpine:* or debian:*)")

        super().__init__(message, context=context, suggestion=suggestion, **kwargs)


class ValidationError(StackbrewGeneratorError):
    """Exception raised for validation failures."""

    def __init__(self, message: str, field: Optional[str] = None, value: Optional[Any] = None, **kwargs):
        context = kwargs.get('context', {})
        if field:
            context['field'] = field
        if value is not None:
            context['value'] = value

        super().__init__(message, context=context, **kwargs)


class ConfigurationError(StackbrewGeneratorError):
    """Exception raised for configuration errors."""

    def __init__(self, message: str, config_key: Optional[str] = None, **kwargs):
        context = kwargs.get('context', {})
        if config_key:
            context['config_key'] = config_key

        suggestion = kwargs.get('suggestion',
            "Check your configuration and environment variables")

        super().__init__(message, context=context, suggestion=suggestion, **kwargs)
