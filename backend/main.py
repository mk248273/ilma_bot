import os
import re
import json
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, select, text
import google.generativeai as genai
from pydantic import ValidationError
from dotenv import load_dotenv

from .database import User, ChatHistory, SessionLocal, DATA_DIR
from .auth import (
    get_password_hash, verify_password, create_access_token, get_current_user,
    get_db, get_current_admin, blacklist_token, ACCESS_TOKEN_EXPIRE_MINUTES
)
from .schemas import (
    UserOut, Token, ChatMessageOut, ChatSessionOut, AdminUserOut,
    AdminMetrics, ErrorResponse, SuccessResponse
)

load_dotenv()


# Simple in-memory rate limiting
class RateLimiter:
    def __init__(self, max_requests: int = 30, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self.requests = {}  # user_id: [(timestamp, count)]
    
    def is_allowed(self, user_id: int) -> bool:
        now = datetime.utcnow()
        if user_id not in self.requests:
            self.requests[user_id] = []
        
        # Clean old requests
        self.requests[user_id] = [
            ts for ts in self.requests[user_id] 
            if (now - ts).total_seconds() < self.window
        ]
        
        if len(self.requests[user_id]) >= self.max_requests:
            return False
        
        self.requests[user_id].append(now)
        return True

rate_limiter = RateLimiter()


# Global exception handlers
def setup_exception_handlers(app: FastAPI):
    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError):
        error_msg = str(exc.orig) if hasattr(exc, 'orig') else str(exc)
        if "UNIQUE constraint failed" in error_msg:
            if "users.email" in error_msg:
                detail = "Email already registered"
            elif "users.username" in error_msg:
                detail = "Username already taken"
            elif "users.student_id" in error_msg:
                detail = "Student ID already registered"
            else:
                detail = "Duplicate entry found"
        else:
            detail = "Database integrity error"
        return JSONResponse(
            status_code=400,
            content={"detail": detail, "code": "INTEGRITY_ERROR"}
        )
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "code": f"HTTP_{exc.status_code}"}
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        errors = exc.errors()
        formatted_errors = []
        for error in errors:
            field = ".".join(str(x) for x in error["loc"])
            formatted_errors.append({
                "field": field,
                "message": error["msg"],
                "type": error["type"]
            })
        return JSONResponse(
            status_code=422,
            content={
                "detail": "Validation error",
                "code": "VALIDATION_ERROR",
                "errors": formatted_errors
            }
        )
    
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "code": "INTERNAL_ERROR"}
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure uploads directories exist
    uploads_base = os.path.join(DATA_DIR, "uploads")
    os.makedirs(os.path.join(uploads_base, "profiles"), exist_ok=True)
    os.makedirs(os.path.join(uploads_base, "chat"), exist_ok=True)
    yield
    # Shutdown cleanup if needed


app = FastAPI(
    title="ILMA AI Bot",
    description="AI Academic Assistant for ILMA University",
    version="2.0.0",
    lifespan=lifespan
)

setup_exception_handlers(app)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("WARNING: GEMINI_API_KEY not set. AI features will not work.")
genai.configure(api_key=GEMINI_API_KEY)
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
model = genai.GenerativeModel(MODEL_NAME)

SYSTEM_PROMPT = """You are the official ILMA AI Assistant for ILMA University. 
Your goal is to assist students, prospective applicants, and faculty with accurate information based on the provided ILMA University context.
- Be professional, polite, and encouraging.
- For academic queries, provide clear and structured information.
- If the user asks about something not in the context, politely suggest they contact the admissions or relevant office.
- Use markdown formatting (bolding, lists, tables) to make your responses readable.
- If an image is uploaded, analyze it in the context of academic support or university surroundings.
- Keep responses concise but comprehensive."""

# Static files configuration with DATA_DIR support
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
os.makedirs(os.path.join(UPLOADS_DIR, "profiles"), exist_ok=True)
os.makedirs(os.path.join(UPLOADS_DIR, "chat"), exist_ok=True)
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")
app.mount("/css", StaticFiles(directory=os.path.join(FRONTEND_DIR, "css")), name="css")
app.mount("/js", StaticFiles(directory=os.path.join(FRONTEND_DIR, "js")), name="js")


@app.get("/")
@app.get("/index.html")
async def read_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.get("/login")
@app.get("/login.html")
async def read_login():
    return FileResponse(os.path.join(FRONTEND_DIR, "login.html"))


@app.get("/register")
@app.get("/register.html")
async def read_register():
    # Check if register.html exists, otherwise use index.html
    reg_path = os.path.join(FRONTEND_DIR, "register.html")
    if os.path.exists(reg_path):
        return FileResponse(reg_path)
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

# Helper to read context
def get_ilma_context():
    try:
        ilma_data_path = os.path.join(os.path.dirname(__file__), "ilma_data.txt")
        with open(ilma_data_path, "r") as f:
            return f.read()
    except:
        return ""


def validate_email_format(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_password_strength(password: str) -> tuple[bool, str]:
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one digit"
    return True, ""


@app.post("/register", response_model=SuccessResponse)
def register(
    username: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(...),
    student_id: str = Form(...),
    email: str = Form(...),
    department: str = Form(...),
    semester: str = Form(...),
    profile_image: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    # Validation
    if len(username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    
    if not validate_email_format(email):
        raise HTTPException(status_code=400, detail="Invalid email format")
    
    is_valid, pwd_error = validate_password_strength(password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=pwd_error)
    
    # Check duplicates before insert (pre-check)
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    
    if db.query(User).filter(User.student_id == student_id).first():
        raise HTTPException(status_code=400, detail="Student ID already registered")
    
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Save profile image if provided
    image_path = None
    if profile_image:
        profiles_dir = os.path.join(UPLOADS_DIR, "profiles")
        os.makedirs(profiles_dir, exist_ok=True)
        ext = os.path.splitext(profile_image.filename)[1].lower()
        if ext not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
            raise HTTPException(status_code=400, detail="Invalid image format")
        image_filename = f"{username}_{uuid.uuid4().hex[:8]}{ext}"
        image_path = f"uploads/profiles/{image_filename}"
        with open(os.path.join(DATA_DIR, image_path), "wb") as f:
            f.write(profile_image.file.read())

    hashed_password = get_password_hash(password)
    new_user = User(
        username=username,
        hashed_password=hashed_password,
        full_name=full_name,
        student_id=student_id,
        email=email,
        department=department,
        semester=semester,
        profile_image=image_path,
        is_admin=False,
        created_at=datetime.utcnow()
    )
    
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return {"message": "User created successfully", "data": {"user_id": new_user.id}}
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Registration failed due to duplicate data")

@app.post("/token", response_model=Token)
def login(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    access_token = create_access_token(data={"sub": user.username})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "username": user.username,
        "profile_image": user.profile_image,
        "is_admin": user.is_admin
    }


@app.post("/auth/logout")
def logout(current_user: User = Depends(get_current_user)):
    # In a full implementation, blacklist the token
    return {"message": "Successfully logged out"}


@app.get("/auth/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@app.get("/chat/history", response_model=List[ChatSessionOut])
def get_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get unique chat sessions for the current user"""
    subquery = select(func.min(ChatHistory.id)).group_by(ChatHistory.session_id)
    sessions = db.query(ChatHistory).filter(
        ChatHistory.id.in_(subquery),
        ChatHistory.user_id == current_user.id
    ).order_by(ChatHistory.timestamp.desc()).all()
    return sessions


@app.get("/chat/session/{session_id}", response_model=List[ChatMessageOut])
def get_session(session_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get all messages in a specific session"""
    messages = db.query(ChatHistory).filter(
        ChatHistory.session_id == session_id,
        ChatHistory.user_id == current_user.id
    ).order_by(ChatHistory.timestamp.asc()).all()
    return messages


@app.delete("/chat/session/{session_id}")
def delete_session(session_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete a chat session"""
    result = db.query(ChatHistory).filter(
        ChatHistory.session_id == session_id,
        ChatHistory.user_id == current_user.id
    ).delete()
    db.commit()
    if result == 0:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session deleted"}


@app.patch("/chat/session/{session_id}")
def rename_session(session_id: str, title: str = Form(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Rename a chat session"""
    result = db.query(ChatHistory).filter(
        ChatHistory.session_id == session_id,
        ChatHistory.user_id == current_user.id
    ).update({ChatHistory.session_title: title})
    db.commit()
    if result == 0:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session renamed"}

@app.post("/chat/send")
async def send_message(
    message: str = Form(...),
    session_id: str = Form(None),
    file: UploadFile = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a message and get streaming AI response"""
    # Rate limiting
    if not rate_limiter.is_allowed(current_user.id):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please slow down.")
    
    # Use existing session_id or create new
    if not session_id:
        session_id = str(uuid.uuid4())
    
    # Prepare context
    context = get_ilma_context()
    
    # Save uploaded file if present
    attachment_url = None
    if file:
        chat_uploads_dir = os.path.join(UPLOADS_DIR, "chat")
        os.makedirs(chat_uploads_dir, exist_ok=True)
        ext = os.path.splitext(file.filename)[1].lower()
        file_filename = f"{current_user.id}_{uuid.uuid4().hex[:8]}{ext}"
        file_path = os.path.join(chat_uploads_dir, file_filename)
        
        file_bytes = await file.read()
        with open(file_path, "wb") as f:
            f.write(file_bytes)
        attachment_url = f"uploads/chat/{file_filename}"
    
    # Save user message to history
    user_msg = ChatHistory(
        user_id=current_user.id,
        session_id=session_id,
        role="user",
        content=message,
        attachment_url=attachment_url
    )
    db.add(user_msg)
    db.commit()

    # Get conversation history for context
    history = db.query(ChatHistory).filter(
        ChatHistory.session_id == session_id,
        ChatHistory.user_id == current_user.id
    ).order_by(ChatHistory.timestamp.asc()).limit(10).all()
    
    # Build conversation context
    conversation_context = ""
    for msg in history[:-1]:  # Exclude the current message we just saved
        role = "User" if msg.role == "user" else "Assistant"
        conversation_context += f"{role}: {msg.content}\n\n"
    
    # Prepare prompt
    full_prompt = f"{SYSTEM_PROMPT}\n\nUNIVERSITY DATA:\n{context}\n\nCONVERSATION HISTORY:\n{conversation_context}\n\nUser: {message}\n\nAssistant:"
    
    contents = [full_prompt]
    if file and file.content_type and file.content_type.startswith("image/"):
        contents.append({"mime_type": file.content_type, "data": file_bytes})

    user_id = current_user.id

    async def generate():
        full_response = ""
        token_count = 0
        try:
            response = await model.generate_content_async(contents, stream=True)
            async for chunk in response:
                if chunk.text:
                    full_response += chunk.text
                    token_count += len(chunk.text.split())
                    yield f"data: {json.dumps({'text': chunk.text})}\n\n"
            
            # Save bot response
            db.add(ChatHistory(
                user_id=user_id,
                session_id=session_id,
                role="bot",
                content=full_response,
                tokens_used=token_count,
                model_used=MODEL_NAME
            ))
            db.commit()
        except Exception as e:
            error_msg = str(e)
            yield f"data: {json.dumps({'text': f'Error: {error_msg}', 'error': True})}\n\n"

    return StreamingResponse(generate(), headers={"X-Session-ID": session_id}, media_type="text/event-stream")

@app.get("/admin/dashboard-data")
def get_admin_data(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get admin dashboard data (admin only)"""
    users = db.query(User).all()
    
    # Calculate metrics
    total_users = len(users)
    total_messages = db.query(ChatHistory).count()
    
    # Active today
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    active_today = db.query(func.count(func.distinct(ChatHistory.user_id))).filter(
        ChatHistory.timestamp >= today
    ).scalar()
    
    # Messages per day (last 7 days)
    messages_per_day = []
    for i in range(7):
        day_start = today - timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        count = db.query(func.count(ChatHistory.id)).filter(
            ChatHistory.timestamp >= day_start,
            ChatHistory.timestamp < day_end
        ).scalar()
        messages_per_day.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "count": count
        })
    messages_per_day.reverse()
    
    # Top departments
    dept_stats = db.query(User.department, func.count(User.id).label("count")).group_by(User.department).all()
    top_departments = [{"name": d[0], "count": d[1]} for d in dept_stats]
    
    # Average messages per user
    avg_messages = total_messages / total_users if total_users > 0 else 0
    
    users_data = [{
        "id": u.id,
        "username": u.username,
        "full_name": u.full_name,
        "student_id": u.student_id,
        "email": u.email,
        "department": u.department,
        "semester": u.semester,
        "is_admin": u.is_admin,
        "created_at": str(u.created_at) if u.created_at else None,
        "last_login": str(u.last_login) if u.last_login else None
    } for u in users]
    
    chats = db.query(ChatHistory).order_by(ChatHistory.timestamp.desc()).limit(200).all()
    chats_data = [{
        "id": c.id,
        "user_id": c.user_id,
        "session_id": c.session_id,
        "role": c.role,
        "content": c.content,
        "timestamp": str(c.timestamp),
        "tokens_used": c.tokens_used,
        "model_used": c.model_used
    } for c in chats]
    
    return {
        "metrics": {
            "total_users": total_users,
            "total_messages": total_messages,
            "active_today": active_today,
            "messages_per_day": messages_per_day,
            "top_departments": top_departments,
            "avg_messages_per_user": round(avg_messages, 2)
        },
        "users": users_data,
        "recent_chats": chats_data
    }


@app.get("/admin/users", response_model=List[AdminUserOut])
def get_all_users(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get all users (admin only)"""
    return db.query(User).all()


@app.delete("/admin/users/{user_id}")
def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Delete a user (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    # Delete user's chat history
    db.query(ChatHistory).filter(ChatHistory.user_id == user_id).delete()
    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully"}


@app.patch("/admin/users/{user_id}/admin")
def toggle_admin_status(
    user_id: int,
    is_admin: bool = Form(...),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Toggle admin status (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id and not is_admin:
        raise HTTPException(status_code=400, detail="Cannot remove your own admin status")
    
    user.is_admin = is_admin
    db.commit()
    return {"message": f"User admin status updated to {is_admin}"}


@app.get("/admin/sessions/{session_id}")
def get_session_admin(
    session_id: str,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get full session transcript (admin only)"""
    messages = db.query(ChatHistory).filter(
        ChatHistory.session_id == session_id
    ).order_by(ChatHistory.timestamp.asc()).all()
    
    if not messages:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return [{
        "id": m.id,
        "user_id": m.user_id,
        "role": m.role,
        "content": m.content,
        "timestamp": str(m.timestamp),
        "tokens_used": m.tokens_used
    } for m in messages]

# Serve remaining frontend files
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=False)
