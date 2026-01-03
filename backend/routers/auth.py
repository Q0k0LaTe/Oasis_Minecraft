"""
Authentication router
FastAPI routes for user registration and login
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db, User, UserSession
from auth.schemas import (
    RegisterRequest, RegisterResponse,
    LoginRequest, LoginResponse,
    UserInfo, SessionInfo,
    SendVerificationCodeRequest, SendVerificationCodeResponse,
    VerifyCodeRequest, VerifyCodeResponse,
)
from utils.password import hash_password, verify_password
from auth.verification import generate_verification_code, store_verification_code, check_code, verify_code, normalize_email
from services.email_service import send_verification_code as send_email_verification_code

router = APIRouter(prefix="/api/auth", tags=["authentication"])


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
    
    # Verify password
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
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

