"""
Security Core - 用户认证与授权核心模块

处理密码哈希、JWT 签发与验证
"""

import os
import bcrypt
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from AICrews.database.models import User
from AICrews.utils.exceptions import ConfigException

# ============================================
# 配置
# ============================================

# JWT 配置 - 必须从环境变量读取
# 注意: 生产环境必须设置 JWT_SECRET_KEY！
# 开发模式如果没有设置会使用生成的临时密钥（重启后所有 token 失效）
def _get_jwt_secret_key() -> str:
    """获取 JWT 签名密钥，如果没有配置则报错或生成临时密钥。"""
    secret_key = os.getenv("JWT_SECRET_KEY")
    if secret_key:
        return secret_key
    # 开发模式: 生成临时密钥并警告
    import warnings
    warnings.warn(
        "JWT_SECRET_KEY not set! Using a generated temporary key. "
        "All existing tokens will be invalidated on restart. "
        "Set JWT_SECRET_KEY environment variable for production.",
        UserWarning,
        stacklevel=2
    )
    from cryptography.fernet import Fernet
    return Fernet.generate_key().decode()


SECRET_KEY = _get_jwt_secret_key()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 默认 24 小时

# OAuth2 配置
# NOTE:
# - `oauth2_scheme` (auto_error=True) is for endpoints that REQUIRE authentication.
#   This allows FastAPI to short-circuit with 401 before resolving other deps (e.g. DB).
# - `oauth2_scheme_optional` (auto_error=False) is for endpoints that allow anonymous access.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


# ============================================
# 密码工具
# ============================================

# Bcrypt has a maximum password length of 72 bytes
# We truncate passwords to 72 bytes to ensure consistent behavior
# This matches the implementation in AICrews.services.user_service
BCRYPT_PASSWORD_MAX_BYTES = 72
BCRYPT_DEFAULT_ROUNDS = 12


def _bcrypt_secret(password: str) -> bytes:
    """
    Convert password to bytes with bcrypt's 72-byte limit.
    
    Bcrypt silently truncates passwords longer than 72 bytes.
    We explicitly truncate here for consistency and to avoid confusion.
    
    Args:
        password: Plain text password
        
    Returns:
        UTF-8 encoded password, truncated to 72 bytes
    """
    return password.encode("utf-8")[:BCRYPT_PASSWORD_MAX_BYTES]


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its bcrypt hash.
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Bcrypt hashed password from database
        
    Returns:
        True if password matches, False otherwise
        
    Note:
        Passwords are truncated to 72 bytes before hashing (bcrypt limitation)
    """
    if not hashed_password:
        return False
    
    try:
        return bcrypt.checkpw(
            _bcrypt_secret(plain_password),
            hashed_password.encode('utf-8')
        )
    except (ValueError, TypeError, AttributeError):
        return False


def get_password_hash(password: str) -> str:
    """
    Generate bcrypt hash for a password.
    
    Args:
        password: Plain text password
        
    Returns:
        Bcrypt hashed password as string
        
    Note:
        Passwords are truncated to 72 bytes before hashing (bcrypt limitation)
        Uses 12 rounds by default (2^12 = 4096 iterations)
    """
    return bcrypt.hashpw(
        _bcrypt_secret(password),
        bcrypt.gensalt(rounds=BCRYPT_DEFAULT_ROUNDS)
    ).decode('utf-8')


# ============================================
# JWT 工具
# ============================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建 JWT access token
    
    Args:
        data: 要编码的数据 (通常包含 sub=user_id)
        expires_delta: 过期时间增量
        
    Returns:
        JWT token 字符串
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    解码 JWT token
    
    Returns:
        解码后的 payload 或 None (如果无效)
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


# ============================================
# 用户服务
# ============================================

def get_user_by_email(session: Session, email: str) -> Optional[User]:
    """通过邮箱获取用户"""
    return session.query(User).filter(User.email == email).first()


def get_user_by_id(session: Session, user_id: int) -> Optional[User]:
    """通过 ID 获取用户"""
    return session.query(User).filter(User.id == user_id).first()


# ============================================
# FastAPI 依赖注入
# ============================================

def get_db():
    """获取数据库会话 (依赖注入)"""
    from AICrews.database.db_manager import DBManager
    db = DBManager()
    try:
        session = db.get_session()
    except ConfigException as e:
        # 将配置错误显式暴露为 503，避免前端收到模糊的 500
        raise HTTPException(status_code=503, detail=str(e))
    try:
        yield session
    finally:
        session.close()


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_db)
) -> User:
    """
    获取当前登录用户 (FastAPI 依赖)
    
    使用方式:
        @router.get("/protected")
        async def protected_route(current_user: User = Depends(get_current_user)):
            return {"user_id": current_user.id}
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    
    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    
    try:
        user_id_int = int(user_id)
    except ValueError:
        raise credentials_exception
    
    user = get_user_by_id(session, user_id_int)
    if user is None:
        raise credentials_exception
    
    return user


async def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    session: Session = Depends(get_db)
) -> Optional[User]:
    """
    获取当前用户 (可选 - 不会抛出异常)
    
    用于既支持登录用户又支持匿名访问的接口
    """
    if not token:
        return None
    
    payload = decode_access_token(token)
    if payload is None:
        return None
    
    user_id: str = payload.get("sub")
    if user_id is None:
        return None
    
    try:
        user_id_int = int(user_id)
    except ValueError:
        return None
    
    return get_user_by_id(session, user_id_int)


async def require_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Require admin privileges (FastAPI dependency).

    Uses the existing `is_superuser` field from User model.

    Usage:
        @router.get("/admin")
        async def admin_route(admin_user: User = Depends(require_admin)):
            return {"user_id": admin_user.id}

    Returns:
        Current user if they have admin privileges.

    Raises:
        HTTPException: 403 if user is not an admin.
    """
    if not getattr(current_user, 'is_superuser', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
