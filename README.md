# 🎤 AI Interview Coach with Voice Feedback

A voice-based mock interviewer that asks role-specific questions, evaluates your answers and tracks your improvement over multiple sessions.

Built during the **AI Agentic Development Internship at Aspire Code AI** (Aug-Sep 2026) by **H. Sunekha** (Intern ID: ACA/AIAGIS/0010/2026).


LIVE DEMO LINK: https://ai-interview-with-coach-voice-feedback-1.onrender.com

## ✨ Features

- **Role-based questions**: AI Engineer, ML Engineer, Data Scientist, Data Analyst, Python Developer and more
- **Resume / job description input**: upload a PDF/TXT resume or paste a job description for personalised questions
- **Voice or text answers**: speak into the mic or type; questions can be read aloud
- **AI evaluation**: scores for clarity, relevance, confidence and technical depth, plus strengths, improvements and a model answer
- **Delivery analysis**: filler-word count, speaking pace (WPM) and STAR-method check
- **Memory across sessions**: weak topics from earlier sessions are used in the next session's questions (SQLite)
- **Progress dashboard**: score trend, filler words per session, weak topics, streak and badges
- **Downloadable report** after every session

## 🧠 How it works

```
Browser (mic / keyboard / resume)
        |
Streamlit UI (app.py)
   |-- voice.py     -> Speech-to-Text (SpeechRecognition) + Text-to-Speech (gTTS)
   |-- analysis.py  -> filler words, speaking pace
   |-- llm.py       -> prompts + Google Gemini API (questions and evaluation)
   |-- memory.py    -> SQLite (sessions, answers, weak topics, streak, badges)
```

## 🛠️ Tech stack

Python 3.10+, Streamlit, Google Gemini API (`google-genai`), SpeechRecognition, gTTS, SQLite, pandas, pypdf, python-dotenv

## 🚀 Setup (Windows)

1. **Clone the repository**
   ```
   git clone https://github.com/<your-username>/<your-repo-name>.git
   cd <your-repo-name>
   ```
2. **Install dependencies**
   ```
   pip install -r requirements.txt
   ```
3. **Add your API key**: get a free key from https://aistudio.google.com/apikey, copy `.env.example` to `.env` and paste the key:
   ```
   copy .env.example .env
   ```
   ```
   GEMINI_API_KEY=your_real_key
   ```
4. **Run the app**
   ```
   streamlit run app.py
   ```
   Open http://localhost:8501 and allow microphone access in the browser.

## 📖 How to use

1. Choose a **role**, **level** and **number of questions** in the sidebar (optionally add a resume or job description).
2. Click **Start interview**.
3. Listen to the question, then record your answer or type it, and click **Submit**.
4. Read the feedback, go to the next question, and finish the session.
5. Open the **Progress** tab to see your improvement over time.

## 📸 Screenshots

| Home | Question | Feedback | Progress |
|------|----------|----------|----------|
| ![Home](screenshots/home.png) | ![Question](screenshots/question.png) | ![Feedback](screenshots/feedback.png) | ![Progress](screenshots/progress.png) |

## ⚠️ Limitations

- English only; speech recognition accuracy depends on microphone, accent and internet.
- Scores come from a language model, so they can vary between runs and are practice guidance, not an official assessment.
- Needs internet access and a Gemini API key (free-tier limits may apply).
- Runs locally; no video or body-language analysis.

## 🔮 Future scope

Tamil and other languages, webcam-based body-language feedback, adaptive follow-up questions, user accounts and cloud deployment, PDF reports.

## 🔒 Security note

Never upload your `.env` file. It is listed in `.gitignore` so your API key stays private.

## 👩‍💻 Author

**H. Sunekha**: AI Agentic Development Intern, Aspire Code AI
