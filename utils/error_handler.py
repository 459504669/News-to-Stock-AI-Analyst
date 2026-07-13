from typing import Optional, Dict, Any
from fastapi import HTTPException
from loguru import logger


class AppException(Exception):
    def __init__(self, message: str, code: int = 500, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


class LLMException(AppException):
    def __init__(self, message: str, code: int = 500, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code, details)


class CollectorException(AppException):
    def __init__(self, message: str, code: int = 503, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code, details)


class DatabaseException(AppException):
    def __init__(self, message: str, code: int = 500, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code, details)


class ValidationException(AppException):
    def __init__(self, message: str, code: int = 400, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code, details)


class ErrorHandler:
    @staticmethod
    def handle_llm_error(error: Exception, provider: str, model: str) -> LLMException:
        error_str = str(error).lower()
        details = {"provider": provider, "model": model}

        if "model_not_found" in error_str or "does not exist" in error_str:
            msg = f"模型 '{model}' 不存在，请检查模型配置"
            logger.error(f"[LLM] {msg}: {error}")
            return LLMException(msg, code=400, details=details)

        if "authentication" in error_str or "api key" in error_str or "unauthorized" in error_str:
            msg = f"API Key 无效或过期，请检查 {provider} 的 API Key"
            logger.error(f"[LLM] {msg}: {error}")
            return LLMException(msg, code=401, details=details)

        if "insufficient_quota" in error_str or "quota" in error_str:
            msg = f"API 额度已用完，请充值或更换 {provider} 的 API Key"
            logger.error(f"[LLM] {msg}: {error}")
            return LLMException(msg, code=429, details=details)

        if "rate_limit" in error_str or "rate limit" in error_str:
            msg = f"API 请求频率过高，请稍后重试"
            logger.warning(f"[LLM] {msg}: {error}")
            return LLMException(msg, code=429, details=details)

        if "timeout" in error_str:
            msg = f"LLM 请求超时，请稍后重试"
            logger.warning(f"[LLM] {msg}: {error}")
            return LLMException(msg, code=504, details=details)

        msg = f"LLM 分析失败: {str(error)[:100]}"
        logger.error(f"[LLM] {msg}: {error}")
        return LLMException(msg, code=500, details=details)

    @staticmethod
    def handle_collector_error(collector_name: str, error: Exception) -> CollectorException:
        error_str = str(error).lower()
        details = {"collector": collector_name}

        if "timeout" in error_str:
            msg = f"采集器 {collector_name} 请求超时"
            logger.warning(f"[Collector] {msg}: {error}")
            return CollectorException(msg, code=504, details=details)

        if "connection" in error_str or "network" in error_str or "dns" in error_str:
            msg = f"采集器 {collector_name} 网络连接失败"
            logger.warning(f"[Collector] {msg}: {error}")
            return CollectorException(msg, code=503, details=details)

        if "403" in str(error) or "forbidden" in error_str:
            msg = f"采集器 {collector_name} 被目标网站拒绝访问（反爬）"
            logger.warning(f"[Collector] {msg}: {error}")
            return CollectorException(msg, code=403, details=details)

        if "404" in str(error) or "not found" in error_str:
            msg = f"采集器 {collector_name} 目标页面不存在"
            logger.warning(f"[Collector] {msg}: {error}")
            return CollectorException(msg, code=404, details=details)

        msg = f"采集器 {collector_name} 执行失败: {str(error)[:100]}"
        logger.error(f"[Collector] {msg}: {error}")
        return CollectorException(msg, code=500, details=details)

    @staticmethod
    def handle_database_error(error: Exception, operation: str) -> DatabaseException:
        error_str = str(error).lower()
        details = {"operation": operation}

        if "unique constraint" in error_str or "duplicate" in error_str:
            msg = f"数据库操作失败：重复数据"
            logger.warning(f"[Database] {msg}: {error}")
            return DatabaseException(msg, code=409, details=details)

        if "no such table" in error_str:
            msg = f"数据库表不存在，请先初始化数据库"
            logger.error(f"[Database] {msg}: {error}")
            return DatabaseException(msg, code=500, details=details)

        if "disk full" in error_str or "cannot open database" in error_str:
            msg = f"数据库存储失败：磁盘空间不足或权限错误"
            logger.error(f"[Database] {msg}: {error}")
            return DatabaseException(msg, code=500, details=details)

        msg = f"数据库 {operation} 失败: {str(error)[:100]}"
        logger.error(f"[Database] {msg}: {error}")
        return DatabaseException(msg, code=500, details=details)

    @staticmethod
    def handle_validation_error(error: Exception, field: Optional[str] = None) -> ValidationException:
        details = {"field": field} if field else {}
        msg = f"参数验证失败: {str(error)[:100]}"
        logger.warning(f"[Validation] {msg}")
        return ValidationException(msg, code=400, details=details)

    @staticmethod
    def to_http_exception(exc: AppException) -> HTTPException:
        return HTTPException(
            status_code=exc.code,
            detail={
                "error": exc.message,
                "code": exc.code,
                "details": exc.details,
            },
        )


def setup_exception_handlers(app):
    @app.exception_handler(AppException)
    async def app_exception_handler(request, exc: AppException):
        return ErrorHandler.to_http_exception(exc).detail

    @app.exception_handler(LLMException)
    async def llm_exception_handler(request, exc: LLMException):
        return ErrorHandler.to_http_exception(exc).detail

    @app.exception_handler(CollectorException)
    async def collector_exception_handler(request, exc: CollectorException):
        return ErrorHandler.to_http_exception(exc).detail

    @app.exception_handler(DatabaseException)
    async def database_exception_handler(request, exc: DatabaseException):
        return ErrorHandler.to_http_exception(exc).detail

    @app.exception_handler(ValidationException)
    async def validation_exception_handler(request, exc: ValidationException):
        return ErrorHandler.to_http_exception(exc).detail
