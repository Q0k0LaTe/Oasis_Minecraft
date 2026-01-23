"""
Subscription-related Pydantic schemas
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr


class SubscribeRequest(BaseModel):
    """Request schema for subscribing to updates"""
    email: EmailStr = Field(..., description="Email address to subscribe")
    source: Optional[str] = Field(None, max_length=50, description="Source of subscription (landing, cli, etc.)")
    utm_source: Optional[str] = Field(None, max_length=255, description="UTM source parameter")
    utm_medium: Optional[str] = Field(None, max_length=255, description="UTM medium parameter")
    utm_campaign: Optional[str] = Field(None, max_length=255, description="UTM campaign parameter")
    utm_term: Optional[str] = Field(None, max_length=255, description="UTM term parameter")
    utm_content: Optional[str] = Field(None, max_length=255, description="UTM content parameter")


class SubscribeResponse(BaseModel):
    """Response schema for subscription"""
    success: bool
    message: str


class UnsubscribeRequest(BaseModel):
    """Request schema for unsubscribing"""
    email: Optional[EmailStr] = Field(None, description="Email address (optional if token is provided)")
    unsubscribe_token: str = Field(..., description="Unsubscribe token")


class UnsubscribeResponse(BaseModel):
    """Response schema for unsubscription"""
    success: bool
    message: str


class SubscriptionResponse(BaseModel):
    """Response schema for a single subscription"""
    id: int
    email: str
    status: str
    source: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime
    unsubscribed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class SubscriptionListResponse(BaseModel):
    """Response schema for subscription list"""
    subscriptions: List[SubscriptionResponse]
    total: int
    page: int
    page_size: int

