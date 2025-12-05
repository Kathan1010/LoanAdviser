# AI Loan Advisor

A multilingual AI-powered loan advisory application with Android frontend and FastAPI backend. The system helps users check loan eligibility through conversational AI, supporting multiple languages including English, Hindi, and Tamil.

## 🚀 Features

- *Conversational AI Interface*: Natural language chat interface for loan inquiries
- *Multilingual Support*: Supports English, Hindi, and Tamil
- *Loan Eligibility Check*: Automated eligibility calculation based on financial profile
- *Multiple Loan Types*: Personal, Home, Car, Education, and Business loans
- *Voice Input*: Speech-to-text support for voice queries
- *Real-time Processing*: Fast response times with pipeline orchestration
- *User Authentication*: Firebase-based authentication system
- *Session Management*: Maintains conversation context across sessions

## 📋 Table of Contents

- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [API Documentation](#api-documentation)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

## 🏗 Architecture

The application follows a client-server architecture:


┌─────────────────┐         HTTP/REST          ┌─────────────────┐
│                 │ ◄─────────────────────────► │                 │
│  Android App    │                             │  FastAPI Server │
│  (Frontend)     │                             │  (Backend)      │
│                 │                             │                 │
└─────────────────┘                             └─────────────────┘
                                                         │
                                                         ▼
                                          ┌─────────────────────────┐
                                          │   Processing Pipeline  │
                                          │                         │
                                          │  • STT (Speech-to-Text) │
                                          │  • Normalization        │
                                          │  • NLU (Extraction)     │
                                          │  • Rules Engine         │
                                          │  • LLM (Gemini)         │
                                          │  • Audit/Logging        │
                                          └─────────────────────────┘


### Backend Pipeline

1. *STT (Speech-to-Text)*: Converts audio input to text using Whisper
2. *Normalization*: Cleans and normalizes text input
3. *NLU (Natural Language Understanding)*: Extracts financial data from user messages
4. *Rules Engine*: Calculates loan eligibility based on business rules
5. *LLM (Large Language Model)*: Generates conversational responses using Google Gemini
6. *Audit/Logging*: Tracks all interactions for analysis

## 🛠 Tech Stack

### Frontend
- *Language*: Kotlin
- *Framework*: Android SDK
- *UI*: Material Design Components
- *Networking*: Retrofit 2.9.0, OkHttp 4.12.0
- *Async Operations*: Kotlin Coroutines
- *Authentication*: Firebase Auth
- *Architecture*: MVVM pattern with Repository layer

### Backend
- *Language*: Python 3.8+
- *Framework*: FastAPI
- *LLM*: Google Gemini API
- *STT*: OpenAI Whisper
- *Server*: Uvicorn (ASGI)
- *Data Processing*: Pydantic, Regex-based NLU

## 📦 Prerequisites

### For Backend
- Python 3.8 or higher
- pip (Python package manager)
- Google Gemini API key ([Get it here](https://makersuite.google.com/app/apikey))
- FFmpeg (for audio processing)

### For Frontend
- Android Studio (latest version)
- JDK 17 or higher
- Android SDK (API level 24+)
- Firebase project setup
- Physical device or emulator (Android 7.0+)

## 🔧 Installation

### Backend Setup

1. *Clone the repository* (if not already done):
   bash
   git clone <repository-url>
   cd LoanAdviser-main
   

2. *Navigate to backend directory*:
   bash
   cd Backend/Backend
   

3. *Create virtual environment* (recommended):
   bash
   python3 -m venv venv
   

4. *Activate virtual environment*:
   
   *On macOS/Linux:*
   bash
   source venv/bin/activate
   
   
   *On Windows:*
   cmd
   venv\Scripts\activate
   

5. *Install dependencies*:
   bash
   pip install -r requirements.txt
   

6. *Set up environment variables*:
   bash
   echo "GEMINI_API_KEY=your-actual-api-key-here" > .env
   
   Replace your-actual-api-key-here with your actual Gemini API key.

### Frontend Setup

1. *Open project in Android Studio*:
   - File → Open → Select Frontend/Frontend directory

2. *Sync Gradle*:
   - File → Sync Project with Gradle Files
   - Wait for dependencies to download

3. *Configure Firebase* (if not already done):
   - Add google-services.json to app/ directory
   - Follow Firebase setup instructions

4. *Update API Base URL* (if needed):
   - Open app/src/main/java/com/example/ailoanadvisor/api/RetrofitClient.kt
   - Update BASE_URL:
     - *Emulator*: http://10.0.2.2:8000 (default)
     - *Physical Device*: http://YOUR_COMPUTER_IP:8000

## ⚙ Configuration

### Backend Configuration

*File*: Backend/Backend/.env
env
GEMINI_API_KEY=your-gemini-api-key-here


### Frontend Configuration

*File*: Frontend/Frontend/app/src/main/java/com/example/ailoanadvisor/api/RetrofitClient.kt

Update BASE_URL based on your setup:
- *Android Emulator*: http://10.0.2.2:8000
- *Physical Device*: http://192.168.1.XXX:8000 (your computer's local IP)

*File*: Frontend/Frontend/app/src/main/res/xml/network_security_config.xml

For production, update to use HTTPS and remove cleartext traffic permissions.

## 🚀 Running the Application

### Start Backend Server

1. *Navigate to backend directory*:
   bash
   cd Backend/Backend
   

2. *Activate virtual environment* (if using venv):
   bash
   source venv/bin/activate  # macOS/Linux
   # OR
   venv\Scripts\activate  # Windows
   

3. *Start the server*:
   bash
   python3 api_endpoint.py
   
   
   Or with uvicorn directly:
   bash
   uvicorn api_endpoint:app --host 0.0.0.0 --port 8000 --reload
   

4. *Verify server is running*:
   - Open browser: http://localhost:8000/docs
   - Health check: http://localhost:8000/health

### Run Android App

1. *Open project in Android Studio*

2. *Connect device or start emulator*

3. *Build and run*:
   - Click Run button (▶) or press Shift + F10
   - Select target device
   - Wait for app to install and launch

4. *Test the integration*:
   - Login/Signup with Firebase
   - Send a chat message: "I need a personal loan of 5 lakh"
   - Check eligibility through the form

## 📚 API Documentation

### Base URL

http://localhost:8000


### Endpoints

#### 1. Health Check
http
GET /health


*Response:*
json
{
  "status": "healthy",
  "service": "Loan Advisor API"
}


#### 2. Chat Endpoint
http
POST /chat
Content-Type: application/json


*Request:*
json
{
  "message": "I need a personal loan of 5 lakh",
  "session_id": "user123",
  "user_language": "english"
}


*Response:*
json
{
  "response": "What is your monthly income?",
  "session_id": "user123",
  "extracted_data": {
    "loan_amount_requested": 500000.0,
    "loan_type": "personal_loan"
  },
  "eligibility_result": null,
  "needs_clarification": true,
  "missing_info": ["monthly income", "age"]
}


#### 3. Audio Chat Endpoint
http
POST /chat/audio
Content-Type: multipart/form-data


*Request:*
- audio_file: Audio file (mp3, wav, m4a, etc.)
- session_id: Session identifier
- user_language: Optional language preference

#### 4. Eligibility Check
http
POST /eligibility/check
Content-Type: application/json


*Request:*
json
{
  "monthly_income": 50000,
  "age": 30,
  "employment_months": 36,
  "loan_type": "personal_loan",
  "loan_amount_requested": 500000,
  "loan_tenure_years": 5,
  "existing_loans_emi": 5000,
  "existing_credit_cards_min_payment": 2000
}


*Response:*
json
{
  "eligibility": {
    "is_eligible": true,
    "eligible_amount": 500000,
    "suggested_emi": 10500,
    "dti_ratio": 0.35
  },
  "message": "Congratulations! You are eligible..."
}


### Interactive API Documentation

Once the server is running, visit:
- *Swagger UI*: http://localhost:8000/docs
- *ReDoc*: http://localhost:8000/redoc

## 📁 Project Structure


LoanAdviser-main/
├── Backend/
│   └── Backend/
│       ├── api_endpoint.py          # FastAPI main application
│       ├── orchestrator.py          # Pipeline orchestration
│       ├── llm_service.py            # Gemini LLM integration
│       ├── rule_engine.py            # Eligibility calculation
│       ├── normalization_service.py  # Text normalization
│       ├── stt_service.py            # Speech-to-text service
│       ├── requirements.txt          # Python dependencies
│       ├── .env                      # Environment variables (create this)
│       ├── venv/                     # Virtual environment (gitignored)
│       └── RUN_PROJECT.md           # Backend-specific docs
│
├── Frontend/
│   └── Frontend/
│       └── app/
│           ├── src/
│           │   └── main/
│           │       ├── java/com/example/ailoanadvisor/
│           │       │   ├── ChatActivity.kt          # Main chat screen
│           │       │   ├── EligibilityActivity.kt   # Eligibility form
│           │       │   ├── LoginActivity.kt         # Authentication
│           │       │   ├── api/                     # API layer
│           │       │   │   ├── ApiModels.kt
│           │       │   │   ├── ApiService.kt
│           │       │   │   └── RetrofitClient.kt
│           │       │   └── repository/              # Data layer
│           │       │       └── ChatRepository.kt
│           │       ├── res/
│           │       │   ├── layout/                  # UI layouts
│           │       │   ├── values/                  # Strings, colors
│           │       │   └── xml/
│           │       │       └── network_security_config.xml
│           │       └── AndroidManifest.xml
│           └── build.gradle                         # Dependencies
│
├── INTEGRATION_GUIDE.md             # Detailed integration guide
├── QUICK_START.md                   # Quick reference
└── README.md                        # This file


## 🔍 Troubleshooting

### Backend Issues

*Issue: "Gemini API key not found"*
- Ensure .env file exists in Backend/Backend/
- Verify GEMINI_API_KEY is set correctly
- Check for typos or extra spaces

*Issue: "Module not found"*
- Activate virtual environment: source venv/bin/activate
- Reinstall dependencies: pip install -r requirements.txt

*Issue: "Port 8000 already in use"*
- Change port: uvicorn api_endpoint:app --port 8001
- Or kill process using port 8000

*Issue: "Whisper model download fails"*
- Check internet connection
- Manually download model if needed
- Verify FFmpeg is installed

### Frontend Issues

*Issue: "Connection refused" or "Network error"*
- Verify backend is running: curl http://localhost:8000/health
- Check BASE_URL in RetrofitClient.kt
- For physical device, use computer's IP address (not localhost)
- Ensure phone and computer are on same WiFi network

*Issue: "Build failed"*
- Sync Gradle: File → Sync Project with Gradle Files
- Clean build: Build → Clean Project
- Invalidate caches: File → Invalidate Caches / Restart

*Issue: "CORS error"*
- Backend already has CORS enabled
- Check backend logs for errors
- Verify allow_origins=["*"] in api_endpoint.py

*Issue: "Timeout error"*
- Increase timeout in RetrofitClient.kt
- Check backend response time
- Verify network connection

### General Issues

*Issue: "App crashes on startup"*
- Check logcat for error messages
- Verify Firebase configuration
- Ensure all permissions are granted

*Issue: "No response from backend"*
- Check backend console for errors
- Verify API key is valid
- Test endpoint directly: curl http://localhost:8000/health

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (git checkout -b feature/AmazingFeature)
3. Commit your changes (git commit -m 'Add some AmazingFeature')
4. Push to the branch (git push origin feature/AmazingFeature)
5. Open a Pull Request

### Code Style

- *Python*: Follow PEP 8 guidelines
- *Kotlin*: Follow Kotlin coding conventions
- *Comments*: Add docstrings/comments for complex logic
- *Testing*: Add tests for new features

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👥 Authors

- Your Name - Initial work

## 🙏 Acknowledgments

- Google Gemini API for LLM capabilities
- OpenAI Whisper for speech-to-text
- FastAPI team for the excellent framework
- Android community for resources and support

## 📞 Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Check existing documentation in INTEGRATION_GUIDE.md
- Review QUICK_START.md for quick reference

---

*Note*: This is a development project. For production use, ensure:
- HTTPS is configured
- API keys are securely stored
- Proper authentication/authorization is implemented
- Error handling and logging are comprehensive
- Security best practices are followed
