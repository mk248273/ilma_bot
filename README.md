# ILMA AI Bot v2.0

A professional, production-grade AI Academic Assistant for ILMA University built with FastAPI, SQLite, and modern web technologies.

![ILMA AI Banner](https://img.shields.io/badge/ILMA-AI%20Assistant-purple?style=for-the-badge&logo=graduation-cap)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![Python](https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python)

## Features

### Core Features
- **AI-Powered Chat**: Powered by Google's Gemini 2.0 Flash for intelligent responses
- **Multi-turn Conversations**: Maintains context for natural, flowing conversations
- **Image Support**: Upload and analyze images within conversations
- **Streaming Responses**: Real-time streaming for smooth user experience
- **Chat History**: Persistent session management with rename/delete functionality
- **Rate Limiting**: Built-in protection against abuse

### User Features
- **Secure Authentication**: JWT-based auth with password hashing (bcrypt)
- **User Profiles**: Custom profile images and comprehensive user data
- **Password Strength**: Enforced strong password requirements
- **Email Validation**: Proper email format verification
- **Department & Semester**: Academic profile tracking

### Admin Features
- **Admin Dashboard**: Comprehensive analytics and monitoring
- **Real-time Metrics**: User counts, message stats, activity tracking
- **Data Visualization**: Chart.js powered graphs for insights
- **User Management**: View, promote/demote, delete users
- **Conversation Monitoring**: View session transcripts
- **Department Analytics**: Breakdown by academic departments

### Technical Features
- **Modern UI**: Glassmorphism design with Tailwind CSS
- **Responsive Design**: Mobile-friendly interface
- **Dark Theme**: Professional dark mode throughout
- **Code Highlighting**: Syntax highlighting for code blocks
- **Copy to Clipboard**: One-click code copying
- **Toast Notifications**: Elegant success/error notifications
- **Safe Error Handling**: Graceful error display without JSON parse crashes

## Project Structure

```
Ilma_bot/
├── backend/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── database.py          # SQLAlchemy models & migrations
│   ├── auth.py              # JWT authentication & security
│   ├── schemas.py           # Pydantic validation models
│   └── seed.py              # Admin user seeder
├── frontend/
│   ├── index.html           # Landing page
│   ├── landing.html         # Modern hero landing
│   ├── login.html           # Authentication page
│   ├── register.html        # Registration with validation
│   ├── chat.html            # ChatGPT-style chat interface
│   ├── admin.html           # Admin dashboard with charts
│   ├── css/
│   │   └── style.css        # Additional styles
│   └── js/
│       ├── auth.js          # Authentication helpers
│       └── chat.js          # (legacy - now in HTML)
├── uploads/                 # File uploads storage
│   ├── profiles/            # User profile images
│   └── chat/                # Chat attachments
├── requirements.txt         # Python dependencies
├── Procfile                 # Railway deployment config
├── railway.json             # Railway service config
├── runtime.txt              # Python version spec
├── .env.example             # Environment variables template
└── README.md                # This file
```

## Quick Start (Local Development)

### Prerequisites
- Python 3.11+
- pip

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd Ilma_bot
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your actual values:
   # - GEMINI_API_KEY (get from Google AI Studio)
   # - SECRET_KEY (generate a random string)
   # - ADMIN_* credentials
   ```

5. **Run the application**
   ```bash
   python -m backend.seed   # Creates admin user
   python run.py
   ```

6. **Access the application**
   - Open browser: http://localhost:8000
   - Landing page: http://localhost:8000/landing.html
   - Login: http://localhost:8000/login.html

### Creating the First Admin

The seed script creates an admin user from your `.env` settings:

```bash
python -m backend.seed
```

Default admin credentials (change in `.env`):
- Username: `admin`
- Password: `SecureAdminPassword123!`

## Railway Deployment

### Prerequisites
- GitHub repository with your code
- [Railway](https://railway.app) account

### Deployment Steps

1. **Push to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git push -u origin main
   ```

2. **Create Railway Project**
   - Go to [Railway Dashboard](https://railway.app/dashboard)
   - Click "New Project"
   - Choose "Deploy from GitHub repo"
   - Select your repository

3. **Add Volume for Persistence**
   - In your Railway project, click "New"
   - Select "Add Volume"
   - Mount path: `/data`
   - Size: 5GB (or as needed)

4. **Configure Environment Variables**
   Go to Variables tab and add:
   ```
   GEMINI_API_KEY=your_gemini_api_key
   SECRET_KEY=your_random_secret_key
   DATA_DIR=/data
   ADMIN_EMAIL=admin@ilma.edu.pk
   ADMIN_PASSWORD=your_secure_password
   ADMIN_USERNAME=admin
   PORT=8000
   ```

5. **Deploy**
   - Railway will automatically detect the `Procfile` and deploy
   - First deploy will fail (no admin) - this is expected

6. **Seed Admin User**
   - Go to your service → "Deploy" tab
   - Click "Deploy" to redeploy after variables are set
   - Or run: `railway run python -m backend.seed`

7. **Get Domain**
   - Railway automatically provides a domain
   - Go to Settings → Domains to view your URL

### Important Railway Notes

- **Volume Required**: SQLite database and uploads persist on the volume at `/data`
- **Free Tier**: Railway offers $5/month free credit which is sufficient for small deployments
- **Auto-deploy**: Every push to main branch triggers automatic redeployment
- **Logs**: View logs in Railway dashboard for debugging

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GEMINI_API_KEY` | Google AI Studio API key | Yes |
| `SECRET_KEY` | JWT signing secret | Yes |
| `DATA_DIR` | Storage directory (use `/data` on Railway) | No (default: `.`) |
| `ADMIN_EMAIL` | Admin user email | For seeding |
| `ADMIN_PASSWORD` | Admin user password | For seeding |
| `ADMIN_USERNAME` | Admin username | For seeding |
| `ADMIN_FULL_NAME` | Admin display name | For seeding |
| `PORT` | Server port | No (default: 8000) |

## API Endpoints

### Authentication
- `POST /register` - Create new account
- `POST /token` - Login (returns JWT)
- `POST /auth/logout` - Logout
- `GET /auth/me` - Get current user

### Chat
- `GET /chat/history` - List user's sessions
- `GET /chat/session/{id}` - Get session messages
- `POST /chat/send` - Send message (streaming)
- `PATCH /chat/session/{id}` - Rename session
- `DELETE /chat/session/{id}` - Delete session

### Admin (Requires admin role)
- `GET /admin/dashboard-data` - Full dashboard data
- `GET /admin/users` - List all users
- `DELETE /admin/users/{id}` - Delete user
- `PATCH /admin/users/{id}/admin` - Toggle admin status
- `GET /admin/sessions/{id}` - View any session

## Database Schema

### Users Table
| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| username | String | Unique login name |
| email | String | Unique email |
| full_name | String | Display name |
| student_id | String | University ID |
| department | String | Academic department |
| semester | String | Current semester |
| hashed_password | String | Bcrypt hash |
| is_admin | Boolean | Admin flag |
| profile_image | String | Image path |
| created_at | DateTime | Registration time |
| last_login | DateTime | Last login time |

### ChatHistory Table
| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| user_id | Integer | Foreign key to users |
| session_id | String | Conversation ID |
| session_title | String | Custom title |
| role | String | "user" or "bot" |
| content | Text | Message content |
| timestamp | DateTime | Message time |
| tokens_used | Integer | Token count |
| model_used | String | AI model name |
| attachment_url | String | File path |

## Bug Fixes & Improvements (v2.0)

### Fixed Issues
- ✅ **Email Duplication**: Added pre-check and safe error handling for duplicate emails
- ✅ **JSON Parse Errors**: Safe JSON parsing with graceful error messages
- ✅ **500 Errors**: Proper exception handlers return structured JSON errors
- ✅ **Admin Guard**: Protected admin endpoints with role verification
- ✅ **Rate Limiting**: In-memory rate limiter prevents API abuse

### New Features
- ✅ **Modern UI**: Complete redesign with Tailwind CSS and glassmorphism
- ✅ **Password Strength**: Visual strength meter with requirements
- ✅ **Multi-step Registration**: Better UX with step-by-step form
- ✅ **Drag-drop Uploads**: Modern file upload with preview
- ✅ **Code Highlighting**: highlight.js for syntax highlighting
- ✅ **Chart.js Analytics**: Visual data representation in admin
- ✅ **Auto-migration**: Database schema updates automatically
- ✅ **Mobile Responsive**: Works on all device sizes

## Security Considerations

1. **Password Hashing**: All passwords hashed with bcrypt
2. **JWT Tokens**: Short-lived access tokens (30 min)
3. **Input Validation**: Pydantic validates all inputs
4. **SQL Injection**: SQLAlchemy ORM prevents injection
5. **XSS Protection**: DOMPurify sanitizes rendered content
6. **Rate Limiting**: Prevents brute force and spam

## Troubleshooting

### Common Issues

**1. "Internal Server Error" on registration**
- Check that email doesn't already exist
- Verify all required fields are filled
- Check backend logs for details

**2. Database errors**
- Ensure `DATA_DIR` is writable
- On Railway, ensure Volume is mounted at `/data`

**3. Gemini API errors**
- Verify `GEMINI_API_KEY` is set correctly
- Check API key has not expired

**4. Static files not loading**
- Ensure `FRONTEND_DIR` path is correct in main.py
- Check browser console for 404 errors

### Getting Help

- Check Railway logs: `railway logs`
- Local debug: `uvicorn backend.main:app --reload --log-level debug`
- Review browser console for frontend errors

## License

This project is for educational use at ILMA University.

## Credits

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- AI powered by [Google Gemini](https://ai.google.dev/)
- UI styled with [Tailwind CSS](https://tailwindcss.com/)
- Icons by [Lucide](https://lucide.dev/)

---

Made with for ILMA University Students
