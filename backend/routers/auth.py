"""
Authentication router
FastAPI routes for user registration and login
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Header, Query
from typing import Optional

from auth.dependencies import get_session_token_from_query_or_header
from sqlalchemy.orm import Session

from database import get_db, User, UserSession
from auth.schemas import (
    RegisterRequest, RegisterResponse,
    LoginRequest, LoginResponse,
    UserInfo, SessionInfo,
    SendVerificationCodeRequest, SendVerificationCodeResponse,
    VerifyCodeRequest, VerifyCodeResponse,
    GoogleLoginRequest, GoogleLoginResponse,
    SetUsernameRequest, SetUsernameResponse,
    LogoutRequest, LogoutResponse,
    LogoutAllResponse,
    DeactivateRequest, DeactivateResponse,
)
from utils.password import hash_password, verify_password
from auth.verification import generate_verification_code, store_verification_code, check_code, verify_code, normalize_email
from services.email_service import send_verification_code as send_email_verification_code
from auth.google_auth import verify_google_token
from config import GOOGLE_CLIENT_ID

router = APIRouter(prefix="/api/auth", tags=["authentication"])


@router.get("/google-client-id")
async def get_google_client_id():
    """
    Get Google OAuth Client ID for frontend
    
    Returns the Google Client ID that frontend needs to initialize Google Sign-In.
    """
    return {
        "client_id": GOOGLE_CLIENT_ID
    }


@router.post("/send-verification-code", response_model=SendVerificationCodeResponse)
async def send_verification_code_endpoint(
    request: SendVerificationCodeRequest,
    db: Session = Depends(get_db)
):
    """
    Send verification code to email address
    
    Generates a 6-digit code, stores it in Redis, and sends it via email.
    Code expires in 10 minutes.
    """
    # Normalize email for consistent storage and lookup
    normalized_email = normalize_email(request.email)
    
    # Check if email is already registered (use normalized email for comparison)
    existing_user = db.query(User).filter(User.email == normalized_email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Generate verification code
    code = generate_verification_code()
    
    # Store code in Redis (normalize_email is called inside store_verification_code)
    if not store_verification_code(normalized_email, code):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store verification code"
        )
    
    # Send email (use original email for display, but store normalized in Redis)
    email_sent = await send_email_verification_code(request.email, code)
    if not email_sent:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email"
        )
    
    return SendVerificationCodeResponse(
        success=True,
        message="Verification code sent to email"
    )


@router.post("/verify-code", response_model=VerifyCodeResponse)
async def verify_code_endpoint(
    request: VerifyCodeRequest
):
    """
    Verify email verification code
    
    Checks if the provided code matches the stored code for the email.
    Code is NOT deleted here, allowing it to be used again during registration.
    """
    is_valid = check_code(request.email, request.code)
    
    return VerifyCodeResponse(
        success=True,
        message="Code verified successfully" if is_valid else "Invalid or expired code",
        valid=is_valid
    )


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new user with email verification
    
    Requires valid verification code before creating account.
    Username and email must be unique.
    """
    # Normalize email for consistent storage and lookup
    normalized_email = normalize_email(request.email)
    
    # Verify email verification code first (normalize_email is called inside verify_code)
    if not verify_code(normalized_email, request.verification_code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code"
        )
    
    # Check if username already exists
    existing_user = db.query(User).filter(User.username == request.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    # Check if email already exists (double check after verification, use normalized email)
    existing_email = db.query(User).filter(User.email == normalized_email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash password
    hashed_password = hash_password(request.password)
    
    # Create new user (store normalized email in database)
    new_user = User(
        username=request.username,
        email=normalized_email,
        password_hash=hashed_password,
        auth_provider='email',
        is_active=True
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return RegisterResponse(
        success=True,
        message="User registered successfully",
        user=UserInfo(
            id=new_user.id,
            username=new_user.username,
            email=new_user.email,
            created_at=new_user.created_at
        )
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login user and create session
    
    Can login with either username or email.
    Automatically creates a new session (like ChatGPT's new conversation).
    """
    # Validate that at least one identifier is provided
    if not request.username and not request.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either username or email must be provided"
        )
    
    # Find user by username or email (normalize email for consistent lookup)
    if request.username:
        user = db.query(User).filter(User.username == request.username).first()
    else:
        normalized_email = normalize_email(request.email)
        user = db.query(User).filter(User.email == normalized_email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Verify password (only for email/password users)
    if user.auth_provider == 'email':
        if not user.password_hash:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        if not verify_password(request.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
    else:
        # Google OAuth users should not use password login
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please use Google login for this account"
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    # Create new session (like ChatGPT's new conversation)
    session_token = str(uuid.uuid4())
    new_session = UserSession(
        user_id=user.id,
        session_token=session_token,
        is_active=True
    )
    
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    
    return LoginResponse(
        success=True,
        message="Login successful",
        session=SessionInfo(
            id=new_session.id,
            token=new_session.session_token,
            name=new_session.name,
            created_at=new_session.created_at
        ),
        user=UserInfo(
            id=user.id,
            username=user.username,
            email=user.email,
            created_at=user.created_at
        )
    )


@router.post("/google-login", response_model=GoogleLoginResponse)
async def google_login(
    request: GoogleLoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login with Google OAuth
    
    Verifies Google ID Token and either:
    - Creates a session for existing users
    - Returns requires_username=true for first-time users
    """
    # Verify Google ID Token
    user_info = verify_google_token(request.id_token)
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google token"
        )
    
    google_id = user_info['sub']
    email = user_info['email']
    name = user_info.get('name')
    picture = user_info.get('picture')
    
    # Normalize email for consistent lookup
    normalized_email = normalize_email(email)
    
    # Check if user exists by google_id
    user = db.query(User).filter(User.google_id == google_id).first()
    
    if user:
        # Existing user - create session and return
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled"
            )
        
        # Update user info if needed (avatar, name might have changed)
        if picture and user.avatar_url != picture:
            user.avatar_url = picture
        if name and not user.username:  # Shouldn't happen, but safety check
            pass  # Don't update username automatically
        
        db.commit()
        
        # Create new session
        session_token = str(uuid.uuid4())
        new_session = UserSession(
            user_id=user.id,
            session_token=session_token,
            is_active=True
        )
        
        db.add(new_session)
        db.commit()
        db.refresh(new_session)
        
        return GoogleLoginResponse(
            success=True,
            message="Login successful",
            requires_username=False,
            session=SessionInfo(
                id=new_session.id,
                token=new_session.session_token,
                name=new_session.name,
                created_at=new_session.created_at
            ),
            user=UserInfo(
                id=user.id,
                username=user.username,
                email=user.email,
                created_at=user.created_at
            )
        )
    else:
        # First-time user - need to set username
        # Check if email already exists (user might have registered with email/password)
        existing_email_user = db.query(User).filter(User.email == normalized_email).first()
        if existing_email_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered with password login. Please use password login or contact support."
            )
        
        return GoogleLoginResponse(
            success=True,
            message="Please set your username to complete registration",
            requires_username=True,
            session=None,
            user=None
        )


@router.post("/set-username", response_model=SetUsernameResponse, status_code=status.HTTP_201_CREATED)
async def set_username(
    request: SetUsernameRequest,
    db: Session = Depends(get_db)
):
    """
    Set username for first-time Google login users
    
    Creates a new user account with Google OAuth information.
    """
    # Verify Google ID Token again for security
    user_info = verify_google_token(request.id_token)
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google token"
        )
    
    google_id = user_info['sub']
    email = user_info['email']
    name = user_info.get('name')
    picture = user_info.get('picture')
    
    # Normalize email
    normalized_email = normalize_email(email)
    
    # Check if user already exists (shouldn't happen, but safety check)
    existing_user = db.query(User).filter(User.google_id == google_id).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists. Please use login endpoint."
        )
    
    # Check if username already exists
    existing_username = db.query(User).filter(User.username == request.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    # Check if email already exists
    existing_email = db.query(User).filter(User.email == normalized_email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    new_user = User(
        username=request.username,
        email=normalized_email,
        password_hash=None,  # Google OAuth users don't have passwords
        google_id=google_id,
        auth_provider='google',
        avatar_url=picture,
        is_active=True
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Create new session
    session_token = str(uuid.uuid4())
    new_session = UserSession(
        user_id=new_user.id,
        session_token=session_token,
        is_active=True
    )
    
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    
    return SetUsernameResponse(
        success=True,
        message="User registered and logged in successfully",
        session=SessionInfo(
            id=new_session.id,
            token=new_session.session_token,
            name=new_session.name,
            created_at=new_session.created_at
        ),
        user=UserInfo(
            id=new_user.id,
            username=new_user.username,
            email=new_user.email,
            created_at=new_user.created_at
        )
    )




@router.post("/logout", response_model=LogoutResponse)
async def logout(
    request: Optional[LogoutRequest] = None,
    session_token: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Logout from current session
    
    Invalidates the current session token by setting is_active=False.
    Supports token via query parameter (backward compatible) or Authorization header.
    
    Idempotent: returns success even if token is already invalid or doesn't exist
    (to prevent information leakage about token existence).
    """
    # Get token from query, header, or request body
    token = get_session_token_from_query_or_header(session_token, authorization)
    if not token and request and request.session_token:
        token = request.session_token
    
    if not token:
        # No token provided - return success (idempotent)
        return LogoutResponse(
            success=True,
            message="Logout successful",
            revoked=False
        )
    
    # Try to find and revoke the session
    session = db.query(UserSession).filter(
        UserSession.session_token == token
    ).first()
    
    revoked = False
    if session and session.is_active:
        session.is_active = False
        db.commit()
        revoked = True
    
    # Always return success (idempotent - don't leak token existence)
    return LogoutResponse(
        success=True,
        message="Logout successful",
        revoked=revoked
    )


@router.post("/logout-all", response_model=LogoutAllResponse)
async def logout_all(
    session_token: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Logout from all sessions
    
    Invalidates all active sessions for the current user.
    Requires a valid session token to identify the user.
    """
    # Get token from query or header
    token = get_session_token_from_query_or_header(session_token, authorization)
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Find the current session to get user_id
    session = db.query(UserSession).filter(
        UserSession.session_token == token,
        UserSession.is_active == True
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session"
        )
    
    user_id = session.user_id
    
    # Revoke all active sessions for this user
    revoked_count = db.query(UserSession).filter(
        UserSession.user_id == user_id,
        UserSession.is_active == True
    ).update({"is_active": False})
    
    db.commit()
    
    return LogoutAllResponse(
        success=True,
        message=f"Logged out from {revoked_count} session(s)",
        revoked_count=revoked_count
    )


@router.post("/deactivate", response_model=DeactivateResponse)
async def deactivate(
    request: DeactivateRequest,
    session_token: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Deactivate user account (soft delete)
    
    Sets User.is_active=False and invalidates all sessions for the user.
    
    Requires additional verification:
    - For email/password users: must provide password
    - For Google OAuth users: must provide valid id_token
    
    Idempotent: can be called multiple times without error.
    """
    # Get token from query or header
    token = get_session_token_from_query_or_header(session_token, authorization)
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Find the current session to get user
    session = db.query(UserSession).filter(
        UserSession.session_token == token,
        UserSession.is_active == True
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session"
        )
    
    user = db.query(User).filter(User.id == session.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if already deactivated (idempotent)
    if not user.is_active:
        return DeactivateResponse(
            success=True,
            message="Account is already deactivated"
        )
    
    # Verify based on auth_provider
    if user.auth_provider == 'email':
        # Email/password users must provide password
        if not request.password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password required for email/password accounts"
            )
        
        if not user.password_hash:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password not set for this account"
            )
        
        if not verify_password(request.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid password"
            )
    
    elif user.auth_provider == 'google':
        # Google OAuth users must provide valid id_token
        if not request.id_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google ID token required for Google OAuth accounts"
            )
        
        # Verify the token and ensure it matches the user
        user_info = verify_google_token(request.id_token)
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Google token"
            )
        
        # Verify the token belongs to this user
        if user_info['sub'] != user.google_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Token does not match this account"
            )
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown auth provider: {user.auth_provider}"
        )
    
    # Deactivate user and all sessions
    user.is_active = False
    
    # Revoke all active sessions for this user
    db.query(UserSession).filter(
        UserSession.user_id == user.id,
        UserSession.is_active == True
    ).update({"is_active": False})
    
    db.commit()
    
    return DeactivateResponse(
        success=True,
        message="Account deactivated successfully"
    )

