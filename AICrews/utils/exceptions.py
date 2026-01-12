"""
Unified Exception Hierarchy for FinanceAICrews
"""

class BaseAppException(Exception):
    """Base exception for all application-specific errors"""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

class DatabaseException(BaseAppException):
    """Fatal database errors (connection failed, table missing)"""
    pass

class ConfigException(BaseAppException):
    """Configuration errors (missing env vars, invalid YAML)"""
    pass

class APIException(BaseAppException):
    """External API call failures (OpenAI, yfinance)"""
    pass

class RecoverableException(BaseAppException):
    """Non-fatal errors that can be retried or ignored (cache miss)"""
    pass

class TaskExecutionException(BaseAppException):
    """Errors during CrewAI task execution"""
    pass
