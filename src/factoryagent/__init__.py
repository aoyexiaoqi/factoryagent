"""FactoryAgent — offline manufacturing-engineering agent workbench.

Natural language triggers *authorized, controlled* tools only. There is no
arbitrary command execution anywhere in this package: every request is
routed to one of the registered tools, its parameters are validated against
a JSON schema, every file path is confined to a workspace root, and file
writes happen only after an explicit confirmation (dry-run by default).
"""

__version__ = "0.1.0"

__all__ = ["__version__"]
