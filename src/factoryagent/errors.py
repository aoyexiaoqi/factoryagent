"""Exception types raised by FactoryAgent."""


class FactoryAgentError(Exception):
    """Base class for all FactoryAgent errors."""


class PathEscapeError(FactoryAgentError):
    """A path tried to escape the configured workspace root."""


class ValidationError(FactoryAgentError):
    """Tool parameters failed schema validation."""


class UnknownToolError(FactoryAgentError):
    """A tool name is not in the registry allowlist."""


class NoRouteError(FactoryAgentError):
    """The natural-language router could not match a request to a tool."""


class ToolExecutionError(FactoryAgentError):
    """A tool ran but could not complete (bad input data, missing file...)."""
