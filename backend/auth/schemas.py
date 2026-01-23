"""
Authentication schemas (Pydantic models)
Request and response models for authentication endpoints
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class RegisterRequest(BaseModel):
    """User registration request"""
    username: str = Field(..., min_length=3, max_length=50, description="Username (3-50 characters)")
    email: EmailStr = Field(..., description="Valid email address")
    password: str = Field(..., min_length=8, max_length=100, description="Password (minimum 8 characters)")
    verification_code: str = Field(..., min_length=6, max_length=6, description="Email verification code (6 digits)")


class SendVerificationCodeRequest(BaseModel):
    """Request to send verification code to email"""
    email: EmailStr = Field(..., description="Email address to send verification code")


class SendVerificationCodeResponse(BaseModel):
    """Response for sending verification code"""
    success: bool
    message: str


class VerifyCodeRequest(BaseModel):
    """Request to verify code"""
    email: EmailStr = Field(..., description="Email address")
    code: str = Field(..., min_length=6, max_length=6, description="Verification code (6 digits)")


class VerifyCodeResponse(BaseModel):
    """Response for code verification"""
    success: bool
    message: str
    valid: bool


class RegisterResponse(BaseModel):
    """User registration response"""
    success: bool
    message: str
    user: Optional['UserInfo'] = None


class LoginRequest(BaseModel):
    """User login request - can use username or email"""
    username: Optional[str] = Field(None, description="Username for login")
    email: Optional[EmailStr] = Field(None, description="Email for login")
    password: str = Field(..., description="Password")
    
    class Config:
        # At least one of username or email must be provided
        schema_extra = {
            "example": {
                "username": "testuser",
                "password": "securepassword123"
            }
        }


class LoginResponse(BaseModel):
    """User login response"""
    success: bool
    message: str
    session: Optional['SessionInfo'] = None
    user: Optional['UserInfo'] = None


class UserInfo(BaseModel):
    """User information in responses"""
    id: UUID
    username: str
    email: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class SessionInfo(BaseModel):
    """Session information in responses"""
    id: int
    token: str
    name: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class GoogleLoginRequest(BaseModel):
    """Google OAuth login request"""
    id_token: str = Field(..., description="Google ID Token from client")


class GoogleLoginResponse(BaseModel):
    """Google OAuth login response"""
    success: bool
    message: str
    requires_username: bool = Field(..., description="Whether user needs to set username (first-time login)")
    session: Optional['SessionInfo'] = None
    user: Optional['UserInfo'] = None


class SetUsernameRequest(BaseModel):
    """Request to set username for first-time Google login"""
    id_token: str = Field(..., description="Google ID Token from client")
    username: str = Field(..., min_length=3, max_length=50, description="Username (3-50 characters)")


class SetUsernameResponse(BaseModel):
    """Response for setting username"""
    success: bool
    message: str
    session: Optional['SessionInfo'] = None
    user: Optional['UserInfo'] = None


class LogoutResponse(BaseModel):
    """Logout response"""
    success: bool
    message: str
    revoked: bool = Field(False, description="Whether a session was actually revoked")


class LogoutAllResponse(BaseModel):
    """Logout all sessions response"""
    success: bool
    message: str
    revoked_count: int = Field(0, description="Number of sessions revoked")


class DeactivateRequest(BaseModel):
    """Deactivate account request"""
    # For email/password users: require password
    password: Optional[str] = Field(None, description="Password (required for email/password users)")
    # For Google OAuth users: require id_token
    id_token: Optional[str] = Field(None, description="Google ID Token (required for Google OAuth users)")


class DeactivateResponse(BaseModel):
    """Deactivate account response"""
    success: bool
    message: str


class DeleteAccountRequest(BaseModel):
    """Delete account request (permanent deletion)"""
    # For email/password users: require password
    password: Optional[str] = Field(None, description="Password (required for email/password users)")
    # For Google OAuth users: require id_token
    id_token: Optional[str] = Field(None, description="Google ID Token (required for Google OAuth users)")
    # Confirmation text to prevent accidental deletion
    confirmation: str = Field(..., description="Type 'DELETE' to confirm permanent account deletion")


class DeleteAccountResponse(BaseModel):
    """Delete account response"""
    success: bool
    message: str


class ReactivateRequest(BaseModel):
    """Reactivate account request"""
    # User identifier (email or username)
    email: Optional[EmailStr] = Field(None, description="Email address of the account to reactivate")
    username: Optional[str] = Field(None, description="Username of the account to reactivate")
    # For email/password users: require password
    password: Optional[str] = Field(None, description="Password (required for email/password users)")
    # For Google OAuth users: require id_token
    id_token: Optional[str] = Field(None, description="Google ID Token (required for Google OAuth users)")


class ReactivateResponse(BaseModel):
    """Reactivate account response"""
    success: bool
    message: str
    user: Optional['UserInfo'] = None


# Update forward references
RegisterResponse.model_rebuild()
LoginResponse.model_rebuild()
GoogleLoginResponse.model_rebuild()
SetUsernameResponse.model_rebuild()
ReactivateResponse.model_rebuild()

