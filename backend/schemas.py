"""
Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime
import re


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=r'^[a-zA-Z0-9_]+$')
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    department: str = Field(..., min_length=1, max_length=50)
    semester: str = Field(..., min_length=1, max_length=20)
    student_id: str = Field(..., min_length=1, max_length=50)
    
    @validator('password', check_fields=False)
    def validate_password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserOut(BaseModel):
    id: int
    username: str
    full_name: str
    email: str
    department: str
    semester: str
    student_id: str
    profile_image: Optional[str] = None
    is_admin: bool = False
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    department: Optional[str] = None
    semester: Optional[str] = None
    profile_image: Optional[str] = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 1800  # 30 minutes
    username: str
    profile_image: Optional[str] = None
    is_admin: bool = False


class TokenPayload(BaseModel):
    sub: Optional[str] = None
    exp: Optional[datetime] = None
    type: Optional[str] = "access"


class ChatMessageOut(BaseModel):
    id: int
    user_id: int
    session_id: str
    session_title: Optional[str] = None
    role: str
    content: str
    timestamp: datetime
    tokens_used: Optional[int] = None
    model_used: Optional[str] = None
    attachment_url: Optional[str] = None
    
    class Config:
        from_attributes = True


class ChatSessionOut(BaseModel):
    session_id: str
    session_title: Optional[str] = None
    role: str
    content: str
    timestamp: datetime
    user_id: int
    
    class Config:
        from_attributes = True


class ChatSendRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: Optional[str] = None


class SessionRenameRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)


class AdminUserOut(BaseModel):
    id: int
    username: str
    full_name: str
    student_id: str
    email: str
    department: str
    semester: str
    is_admin: bool
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class AdminMetrics(BaseModel):
    total_users: int
    total_messages: int
    active_today: int
    messages_per_day: List[dict]
    top_departments: List[dict]
    avg_messages_per_user: float


class ErrorResponse(BaseModel):
    detail: str
    code: Optional[str] = None
    field: Optional[str] = None


class SuccessResponse(BaseModel):
    message: str
    data: Optional[dict] = None


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)
    
    @validator('new_password')
    def validate_new_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        return v
