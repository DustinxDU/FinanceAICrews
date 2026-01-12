"""
Authentication API Routes - 用户认证路由

提供注册、登录、用户信息接口
业务逻辑已下沉至 AICrews.services.user_service
"""

import asyncio
import logging
import os
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from AICrews.schemas.user import (
    UserCreate,
    UserLogin,
    UserResponse,
    Token,
)
from AICrews.schemas.common import ErrorResponse
from AICrews.database.models import User
from AICrews.services.user_service import UserService

from backend.app.security import (
    get_db,
    get_current_user,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)

logger = logging.getLogger(__name__)


# ============================================
# LLM Virtual Key Provisioning
# ============================================

async def provision_user_keys_with_timeout(
    user_id: int,
    timeout_seconds: float = 3.0,
) -> bool:
    """
    为新用户配置 LiteLLM 虚拟密钥，带超时降级。

    Args:
        user_id: 新创建的用户 ID
        timeout_seconds: 超时时间（秒），超时后降级返回

    Returns:
        True 如果成功配置，False 如果超时或失败（将由后台 reconcile 完成）

    Note:
        - Provisioning 失败不会阻止用户注册成功
        - 超时或失败时，后台 reconcile 任务会在几分钟内完成配置
        - 首次 Crew 执行有 retry 机制处理未就绪的 key
    """
    # 检查 LiteLLM Proxy 是否配置
    master_key = os.getenv("LITELLM_PROXY_MASTER_KEY")
    if not master_key:
        logger.debug(
            f"LITELLM_PROXY_MASTER_KEY not set, skipping provisioning for user {user_id}"
        )
        return False

    try:
        async with asyncio.timeout(timeout_seconds):
            from AICrews.services.provisioner_service import ProvisionerService
            from AICrews.services.litellm_admin_client import LiteLLMAdminClient
            from AICrews.database.db_manager import get_db_session

            # 创建 admin client 和 provisioner
            admin_client = LiteLLMAdminClient()
            provisioner = ProvisionerService(admin_client=admin_client)

            try:
                # 使用异步会话
                async with get_db_session() as db:
                    # 1. 创建 PROVISIONING 记录
                    await provisioner.provision_user(user_id=user_id, db=db)

                    # 2. 立即执行 reconcile 完成配置
                    stats = await provisioner.reconcile(db=db, limit=10)

                    logger.info(
                        f"Provisioned virtual keys for user {user_id}: "
                        f"success={stats['success']}, failed={stats['failed']}"
                    )

                    return stats["success"] > 0

            finally:
                await admin_client.close()

    except asyncio.TimeoutError:
        logger.warning(
            f"Provisioning timeout ({timeout_seconds}s) for user {user_id}, "
            "will complete in background reconcile"
        )
        return False

    except Exception as e:
        logger.error(
            f"Provisioning failed for user {user_id}: {e}",
            exc_info=True
        )
        return False

router = APIRouter(prefix="/auth", tags=["Authentication"])

def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(db)


# ============================================
# 认证接口
# ============================================

@router.post(
    "/register",
    response_model=Token,
    responses={400: {"model": ErrorResponse}},
    summary="用户注册",
    description="创建新用户账户并返回 JWT Token",
)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    service: UserService = Depends(get_user_service),
):
    """
    用户注册

    - **email**: 用户邮箱 (唯一)
    - **password**: 密码 (至少6位)

    成功后返回 JWT Token，可直接用于后续请求
    """
    # 创建用户
    try:
        user = service.create_user(user_data)
        logger.info(f"New user registered: {user.email}")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to create user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="用户创建失败"
        )

    # 配置 LLM 虚拟密钥（3秒超时，失败不影响注册）
    await provision_user_keys_with_timeout(
        user_id=user.id,
        timeout_seconds=3.0,
    )

    # 生成 Token
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@router.post(
    "/login",
    response_model=Token,
    responses={401: {"model": ErrorResponse}},
    summary="用户登录",
    description="验证用户凭据并返回 JWT Token",
)
async def login(
    user_data: UserLogin,
    service: UserService = Depends(get_user_service),
):
    """
    用户登录
    
    - **email**: 用户邮箱
    - **password**: 密码
    
    返回 JWT Token，有效期默认 24 小时
    """
    user = service.authenticate(user_data.email, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 生成 Token
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    logger.info(f"User logged in: {user.email}")
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@router.post(
    "/login/oauth2",
    response_model=Token,
    include_in_schema=False,
    summary="OAuth2 兼容登录",
    description="兼容 OAuth2PasswordRequestForm 的登录接口 (用于 Swagger UI)",
)
async def login_oauth2(
    form_data: OAuth2PasswordRequestForm = Depends(),
    service: UserService = Depends(get_user_service),
):
    """
    OAuth2 兼容登录接口
    
    用于支持 Swagger UI 的 Authorize 功能
    username 字段接收邮箱
    """
    user = service.authenticate(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@router.get(
    "/me",
    response_model=UserResponse,
    responses={401: {"model": ErrorResponse}},
    summary="获取当前用户信息",
    description="获取当前登录用户的详细信息",
)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    """
    获取当前用户信息
    
    需要在 Header 中携带 Bearer Token:
    `Authorization: Bearer <token>`
    """
    return UserResponse.model_validate(current_user)


@router.post(
    "/refresh",
    response_model=Token,
    responses={401: {"model": ErrorResponse}},
    summary="刷新 Token",
    description="使用现有 Token 获取新 Token",
)
async def refresh_token(
    current_user: User = Depends(get_current_user),
):
    """
    刷新 Token
    
    使用当前有效的 Token 获取新的 Token
    延长登录有效期
    """
    access_token = create_access_token(
        data={"sub": str(current_user.id)},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(current_user)
    )
