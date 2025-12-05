# How to Run the Project

## Option 1: Interactive CLI (Recommended for Testing)

Run the orchestrator's terminal interface:

```bash
python3 orchestrator.py
```

This will start an interactive chat where you can:
- Type your loan queries
- See the full pipeline in action
- Get eligibility results and LLM responses

**Example conversation:**
```
👤 You: I need a personal loan of 5 lakh rupees. My income is 50000 per month. I am 30 years old.

🤖 Assistant: [LLM response with eligibility]
```

Type `exit` or `quit` to end.

---

## Option 2: FastAPI Server (For Frontend Integration)

Start the API server:

```bash
python3 api_endpoint.py
```

Or with uvicorn directly:

```bash
uvicorn api_endpoint:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at:
- **URL**: http://localhost:8000
- **Docs**: http://localhost:8000/docs (Swagger UI)
- **Health Check**: http://localhost:8000/health

### API Endpoints:

1. **POST /chat** - Main chat endpoint
   ```json
   {
     "message": "I need a personal loan of 5 lakh",
     "session_id": "user123",
     "user_language": "english"
   }
   ```

2. **POST /eligibility/check** - Direct eligibility check
   ```json
   {
     "monthly_income": 50000,
     "age": 30,
     "employment_months": 36,
     "loan_type": "personal_loan",
     "loan_amount_requested": 500000,
     "loan_tenure_years": 5
   }
   ```

3. **GET /health** - Health check

---

## Option 3: Test Individual Components

### Test STT:
```bash
python3 test_stt.py [audio_file.mp3]
```

### Test NLU:
```bash
python3 -c "from api_endpoint import extract_financial_data; print(extract_financial_data('I need 5 lakh loan'))"
```

### Test Rules Engine:
```bash
python3 rule_engine.py
```

### Test LLM:
```bash
python3 simple_chat.py
```

---

## Prerequisites

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up API key:**
   - Create `.env` file in project root
   - Add: `GEMINI_API_KEY=your-actual-api-key-here`
   - Get key from: https://makersuite.google.com/app/apikey

3. **Whisper model** (for STT):
   - Will download automatically on first use (~72MB for 'base' model)
   - Requires internet connection for first download

---

## Troubleshooting

### Issue: "Gemini API key not found"
- Check `.env` file exists and has `GEMINI_API_KEY=your-key`
- Make sure `python-dotenv` is installed

### Issue: "Whisper not installed"
- Run: `pip install openai-whisper ffmpeg-python`

### Issue: SSL certificate errors (macOS)
- The code handles this automatically, but if issues persist:
  - Run: `/Applications/Python\ 3.13/Install\ Certificates.command`

### Issue: LLM stuck asking for tenure
- This has been fixed! The system now uses default tenure if not provided
- Make sure you're using the latest code

---

## Pipeline Flow

When you run the orchestrator, it processes:

1. **STT** (if audio provided) → Text
2. **Normalization** → Cleaned text
3. **NLU** → Intent + Extracted data
4. **Rules Engine** → Eligibility calculation
5. **OCR** (optional) → Document data
6. **LLM** → Friendly response
7. **DB/Audit** → Logging

All stages have error handling and fallbacks!

