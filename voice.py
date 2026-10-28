import io

try:
    import speech_recognition as sr
except Exception:  # library missing
    sr = None

try:
    from gtts import gTTS
except Exception:
    gTTS = None


def speak(text: str):
    """Text -> mp3 bytes. Returns None if it fails (no internet etc.)."""
    if gTTS is None or not text:
        return None
    try:
        fp = io.BytesIO()
        gTTS(text=text[:700], lang="en", tld="co.in").write_to_fp(fp)
        return fp.getvalue()
    except Exception:
        return None


def transcribe(wav_bytes: bytes):
    """Speech -> text. Returns (text, error_message)."""
    if sr is None:
        return "", "SpeechRecognition library not installed."
    r = sr.Recognizer()
    try:
        with sr.AudioFile(io.BytesIO(wav_bytes)) as src:
            audio = r.record(src)
        return r.recognize_google(audio, language="en-IN"), ""
    except sr.UnknownValueError:
        return "", "I could not understand the audio. Speak clearly or type your answer."
    except sr.RequestError:
        return "", "Speech service not reachable. Check internet or type your answer."
    except Exception as e:
        return "", f"Audio problem: {str(e)[:100]}"