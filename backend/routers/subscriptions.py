"""
Subscriptions Router
FastAPI routes for email subscription management

Allows users to subscribe to product updates without registration.
Supports unsubscribe functionality and admin management.
"""
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from database import get_db, EmailSubscription
from auth.verification import normalize_email
from auth.admin import get_admin_user
from auth.dependencies import get_current_user
from schemas.subscription import (
    SubscribeRequest,
    SubscribeResponse,
    UnsubscribeRequest,
    UnsubscribeResponse,
    SubscriptionResponse,
    SubscriptionListResponse,
)
from utils.rate_limit import check_rate_limit, get_client_ip

router = APIRouter(prefix="/api/subscriptions", tags=["subscriptions"])


def validate_email_format(email: str) -> bool:
    """
    Basic email format validation
    
    Note: Pydantic's EmailStr already validates format, but this provides
    an additional check for security.
    """
    if not email or "@" not in email:
        return False
    parts = email.split("@")
    if len(parts) != 2:
        return False
    local, domain = parts
    if not local or not domain or "." not in domain:
        return False
    return True


@router.post("", response_model=SubscribeResponse, status_code=status.HTTP_201_CREATED)
async def subscribe(
    request: SubscribeRequest,
    http_request: Request,
    db: Session = Depends(get_db)
):
    """
    订阅产品更新通知
    
    用户无需注册登录即可订阅。同一邮箱重复订阅会幂等返回成功。
    
    **默认值**：
    - 不需要登录
    - 不需要邮箱验证（只做格式校验）
    - 不允许重复订阅（同一 email 幂等）
    - 记录来源信息（source/utm、ip、user_agent）
    
    **安全防护**：
    - 按 IP 和邮箱限流（防止滥用）
    - 返回信息不泄露邮箱是否存在（防枚举）
    """
    # Normalize email
    normalized_email = normalize_email(request.email)
    
    # Rate limiting by IP
    client_ip = get_client_ip(http_request)
    ip_key = f"subscribe:ip:{client_ip}"
    allowed, _ = check_rate_limit(ip_key, max_requests=5, window_seconds=60)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later."
        )
    
    # Rate limiting by email
    email_key = f"subscribe:email:{normalized_email}"
    allowed, _ = check_rate_limit(email_key, max_requests=3, window_seconds=300)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later."
        )
    
    # Check if subscription already exists
    existing = db.query(EmailSubscription).filter(
        EmailSubscription.email == normalized_email
    ).first()
    
    if existing:
        # If already subscribed, return success (idempotent)
        if existing.status == "subscribed":
            return SubscribeResponse(
                success=True,
                message="You are already subscribed to updates."
            )
        # If unsubscribed, reactivate
        elif existing.status == "unsubscribed":
            existing.status = "subscribed"
            existing.unsubscribed_at = None
            existing.updated_at = datetime.utcnow()
            # Update source info if provided
            if request.source:
                existing.source = request.source
            if request.utm_source:
                existing.utm_source = request.utm_source
            if request.utm_medium:
                existing.utm_medium = request.utm_medium
            if request.utm_campaign:
                existing.utm_campaign = request.utm_campaign
            if request.utm_term:
                existing.utm_term = request.utm_term
            if request.utm_content:
                existing.utm_content = request.utm_content
            existing.ip_address = client_ip
            existing.user_agent = http_request.headers.get("User-Agent")
            db.commit()
            return SubscribeResponse(
                success=True,
                message="You have been resubscribed to updates."
            )
    
    # Create new subscription
    unsubscribe_token = str(uuid.uuid4())
    subscription = EmailSubscription(
        email=normalized_email,
        status="subscribed",
        unsubscribe_token=unsubscribe_token,
        source=request.source or "unknown",
        utm_source=request.utm_source,
        utm_medium=request.utm_medium,
        utm_campaign=request.utm_campaign,
        utm_term=request.utm_term,
        utm_content=request.utm_content,
        ip_address=client_ip,
        user_agent=http_request.headers.get("User-Agent")
    )
    
    try:
        db.add(subscription)
        db.commit()
        db.refresh(subscription)
    except Exception as e:
        db.rollback()
        # Check if it's a unique constraint violation (race condition)
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            # Another request created it, return success (idempotent)
            return SubscribeResponse(
                success=True,
                message="You are already subscribed to updates."
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create subscription"
        )
    
    return SubscribeResponse(
        success=True,
        message="Successfully subscribed to updates."
    )


@router.post("/unsubscribe", response_model=UnsubscribeResponse)
async def unsubscribe(
    request: UnsubscribeRequest,
    http_request: Request,
    db: Session = Depends(get_db)
):
    """
    退订产品更新通知
    
    使用 unsubscribe_token 或 email + token 进行退订。
    返回信息不泄露订阅状态（防枚举）。
    """
    # Rate limiting by IP
    client_ip = get_client_ip(http_request)
    ip_key = f"unsubscribe:ip:{client_ip}"
    allowed, _ = check_rate_limit(ip_key, max_requests=10, window_seconds=60)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later."
        )
    
    # Find subscription by token (preferred) or email + token
    subscription = None
    if request.unsubscribe_token:
        subscription = db.query(EmailSubscription).filter(
            EmailSubscription.unsubscribe_token == request.unsubscribe_token
        ).first()
        
        # If email is also provided, verify it matches
        if subscription and request.email:
            normalized_email = normalize_email(request.email)
            if subscription.email != normalized_email:
                # Don't reveal that email doesn't match (security)
                subscription = None
    
    # If not found by token, try email + token
    if not subscription and request.email:
        normalized_email = normalize_email(request.email)
        subscription = db.query(EmailSubscription).filter(
            EmailSubscription.email == normalized_email,
            EmailSubscription.unsubscribe_token == request.unsubscribe_token
        ).first()
    
    # Always return success to prevent enumeration
    if not subscription:
        return UnsubscribeResponse(
            success=True,
            message="If you were subscribed, you have been unsubscribed."
        )
    
    # Unsubscribe
    if subscription.status != "unsubscribed":
        subscription.status = "unsubscribed"
        subscription.unsubscribed_at = datetime.utcnow()
        subscription.updated_at = datetime.utcnow()
        db.commit()
    
    return UnsubscribeResponse(
        success=True,
        message="You have been unsubscribed from updates."
    )


@router.get("/admin/list", response_model=SubscriptionListResponse)
async def list_subscriptions(
    status_filter: Optional[str] = Query(None, description="Filter by status (subscribed, unsubscribed, bounced)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Page size"),
    db: Session = Depends(get_db),
    admin_user = Depends(get_admin_user)
):
    """
    管理员接口：获取订阅列表
    
    需要管理员权限。支持分页、按状态过滤、按创建时间排序。
    """
    # Build query
    query = db.query(EmailSubscription)
    
    # Apply status filter
    if status_filter:
        query = query.filter(EmailSubscription.status == status_filter)
    
    # Get total count
    total = query.count()
    
    # Apply pagination and ordering
    subscriptions = query.order_by(
        EmailSubscription.created_at.desc()
    ).offset((page - 1) * page_size).limit(page_size).all()
    
    return SubscriptionListResponse(
        subscriptions=[SubscriptionResponse.model_validate(s) for s in subscriptions],
        total=total,
        page=page,
        page_size=page_size
    )

