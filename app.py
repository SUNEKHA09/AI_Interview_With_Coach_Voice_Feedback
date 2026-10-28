import html

import pandas as pd
import streamlit as st

import analysis
import llm
import memory
import voice

st.set_page_config(page_title="AI Interview Coach", page_icon="🎤", layout="wide")
memory.init()

ROLES = ["AI Engineer", "ML Engineer", "Data Scientist", "Data Analyst", "Python Developer",
         "Web Developer", "Java Developer", "Software Tester", "Digital Marketing",
         "HR / General Fresher"]
LEVELS = ["Fresher", "Junior (1-3 yrs)", "Senior (3+ yrs)"]

st.markdown("""
<style>
footer {visibility: hidden;}
#MainMenu {visibility: hidden;}
.block-container {padding-top: 1.5rem; max-width: 1150px;}
.hero {padding: 1.5rem 1.8rem; border-radius: 18px; margin-bottom: 1.2rem;
       background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 55%, #db2777 100%); color: #fff;}
.hero h1 {margin: 0; font-size: 2rem; color: #fff; padding: 0;}
.hero p {margin: .4rem 0 0; opacity: .92; font-size: 1.02rem;}
.qcard {padding: 1.3rem 1.5rem; border-radius: 16px; font-size: 1.3rem; font-weight: 600;
        border: 1px solid rgba(124,58,237,.35); background: rgba(124,58,237,.09); margin: .4rem 0 1rem;}
.pill {display: inline-block; padding: .25rem .9rem; border-radius: 999px; color: #fff;
       font-weight: 700; font-size: 1.15rem;}
.card {padding: 1rem 1.2rem; border-radius: 14px; border: 1px solid rgba(128,128,128,.25);
       background: rgba(128,128,128,.06); height: 100%;}
.card h4 {margin: 0 0 .4rem; padding: 0;}
.small {opacity: .75; font-size: .9rem;}
</style>
""", unsafe_allow_html=True)

DEFAULTS = dict(started=False, finished=False, idx=0, questions=[], audio={}, played=[],
                results=[], last=None, role="", level="", total=4, context="")
for k, v in DEFAULTS.items():
    st.session_state.setdefault(k, v)
S = st.session_state


# ---------------- helpers ----------------
def score_color(s):
    return "#16a34a" if s >= 8 else "#d97706" if s >= 6 else "#dc2626"


def pill(s):
    return f"<span class='pill' style='background:{score_color(s)}'>{s}/10</span>"


def read_resume(file):
    if file is None:
        return ""
    try:
        if file.name.lower().endswith(".pdf"):
            from pypdf import PdfReader
            reader = PdfReader(file)
            return " ".join((p.extract_text() or "") for p in reader.pages).strip()
        return file.getvalue().decode("utf-8", errors="ignore").strip()
    except Exception:
        return None


def build_report():
    lines = [f"# Interview Report: {S.role} ({S.level})", ""]
    for i, r in enumerate(S.results, 1):
        ev = r["ev"]
        lines += [f"## Q{i}. {r['q']}", f"**Your answer:** {r['answer']}",
                  f"**Score:** {ev['score']}/10",
                  f"**Strengths:** {'; '.join(ev['strengths'])}",
                  f"**Improve:** {'; '.join(ev['improvements'])}",
                  f"**Better answer:** {ev['better_answer']}", ""]
    return "\n".join(lines)


def go_next():
    if S.idx + 1 >= S.total:
        if S.results:
            memory.save_session(S.role, S.level, S.results)
        S.finished = True
    else:
        S.idx += 1
    S.last = None


def process_answer(audio, typed):
    """Returns error message or '' on success."""
    typed = (typed or "").strip()
    with st.status("Processing your answer...", expanded=True) as status:
        answer, dur = typed, 0.0
        if not answer and audio is not None:
            st.write("🎧 Transcribing your voice...")
            wav = audio.getvalue()
            answer, err = voice.transcribe(wav)
            dur = analysis.audio_duration(wav)
            if not answer:
                status.update(label="Could not read audio", state="error")
                return err
        if not answer:
            status.update(label="No answer found", state="error")
            return "Please record your voice or type an answer first."
        st.write("🧠 AI is evaluating your answer...")
        try:
            ev = llm.evaluate(S.role, S.level, S.questions[S.idx], answer)
        except llm.LLMError as e:
            status.update(label="AI problem", state="error")
            return str(e)
        S.last = dict(q=S.questions[S.idx], answer=answer, ev=ev,
                      fillers=analysis.count_fillers(answer),
                      wpm=analysis.words_per_minute(answer, dur))
        S.results.append(S.last)
        status.update(label="Done!", state="complete")
    return ""


# ---------------- views ----------------
def welcome_view():
    st.subheader("How it works")
    c = st.columns(4)
    steps = [("1️⃣ Setup", "Pick role, level and optionally upload your resume."),
             ("2️⃣ Listen", "AI interviewer asks you questions aloud."),
             ("3️⃣ Answer", "Speak into the mic or type your answer."),
             ("4️⃣ Improve", "Get scores, tips, a model answer and track progress.")]
    for col, (t, d) in zip(c, steps):
        col.markdown(f"<div class='card'><h4>{t}</h4><span class='small'>{d}</span></div>",
                     unsafe_allow_html=True)
    st.write("")
    st.info("👈 Choose your role in the sidebar and click **Start interview**.")


def question_view():
    i = S.idx
    st.progress(i / S.total, text=f"Question {i + 1} of {S.total}  •  {S.role}  •  {S.level}")
    st.markdown(f"<div class='qcard'>🧑‍💼 {html.escape(S.questions[i])}</div>", unsafe_allow_html=True)

    if S.last is None:
        if S.get("speak", True):
            if i not in S.audio:
                S.audio[i] = voice.speak(S.questions[i])
            if S.audio[i]:
                st.audio(S.audio[i], format="audio/mp3", autoplay=(i not in S.played))
                if i not in S.played:
                    S.played.append(i)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("##### 🎙️ Speak your answer")
            audio = st.audio_input("Click the mic, answer, then stop", key=f"aud{i}")
        with c2:
            st.markdown("##### ⌨️ Or type your answer")
            typed = st.text_area("Type here", key=f"txt{i}", height=140, label_visibility="collapsed")
        b1, b2, _ = st.columns([1, 1, 3])
        submit = b1.button("✅ Submit", type="primary", key=f"sub{i}")
        skip = b2.button("⏭️ Skip", key=f"skip{i}")
        if skip:
            go_next()
            st.rerun()
        if submit:
            err = process_answer(audio, typed)
            if err:
                st.error(err)
            else:
                st.rerun()
    else:
        feedback_view()


def feedback_view():
    r = S.last
    ev = r["ev"]
    st.markdown(f"**Your score:** {pill(ev['score'])}", unsafe_allow_html=True)
    st.write("")
    st.caption("📝 What I heard: " + r["answer"])
    m = st.columns(4)
    for col, k in zip(m, ["clarity", "relevance", "confidence", "technical"]):
        col.metric(k.title(), f"{ev[k]}/10")
    s1, s2, s3 = st.columns(3)
    s1.markdown(f"<div class='card'><h4>⏱️ Pace</h4>{analysis.pace_tip(r['wpm'])}</div>", unsafe_allow_html=True)
    fl = ", ".join(f"{k} ×{v}" for k, v in r["fillers"].items()) or "None 👏"
    s2.markdown(f"<div class='card'><h4>🗣️ Filler words</h4>{html.escape(fl)}</div>", unsafe_allow_html=True)
    star = "⭐ Good structure (STAR)" if ev["star_used"] else "⚠️ Try the STAR method"
    s3.markdown(f"<div class='card'><h4>🧩 Structure</h4>{star}</div>", unsafe_allow_html=True)
    st.write("")
    g, b = st.columns(2)
    with g:
        st.success("**💪 Strengths**\n\n" + "\n".join(f"- {x}" for x in ev["strengths"]) if ev["strengths"] else "**💪 Strengths**\n\n- Keep going!")
    with b:
        st.warning("**🛠️ Improve**\n\n" + "\n".join(f"- {x}" for x in ev["improvements"]) if ev["improvements"] else "**🛠️ Improve**\n\n- Add more detail")
    with st.expander("💡 Model answer"):
        st.write(ev["better_answer"])
        if st.button("🔊 Listen", key=f"listen{S.idx}"):
            ba = voice.speak(ev["better_answer"])
            if ba:
                st.audio(ba, format="audio/mp3", autoplay=True)
            else:
                st.info("Audio not available right now.")
    last = S.idx + 1 >= S.total
    if st.button("🏁 Finish interview" if last else "➡️ Next question", type="primary", key=f"next{S.idx}"):
        go_next()
        st.rerun()


def finish_view():
    if not S.results:
        st.info("You skipped every question. Start a new interview from the sidebar.")
        return
    avg = round(sum(r["ev"]["score"] for r in S.results) / len(S.results), 1)
    st.balloons()
    st.markdown(f"## 🏁 Session complete  {pill(avg)}", unsafe_allow_html=True)
    fillers = sum(sum(r["fillers"].values()) for r in S.results)
    best = max(S.results, key=lambda r: r["ev"]["score"])
    worst = min(S.results, key=lambda r: r["ev"]["score"])
    c = st.columns(3)
    c[0].metric("Average score", f"{avg}/10")
    c[1].metric("Filler words", fillers)
    c[2].metric("Answered", f"{len(S.results)}/{S.total}")
    st.write(f"🏆 **Best answer:** {best['q']}")
    st.write(f"🎯 **Practise more:** {worst['q']}")
    df = pd.DataFrame([{"Question": r["q"], "Score": r["ev"]["score"], "Fillers": sum(r["fillers"].values()),
                        "WPM": r["wpm"] or "-"} for r in S.results])
    st.dataframe(df, hide_index=True)
    st.download_button("⬇️ Download full report", build_report(), "interview_report.md", "text/markdown")
    st.caption("Open the Progress tab to see your improvement over sessions.")


def progress_view():
    rows = memory.sessions()
    if not rows:
        st.info("No sessions yet. Complete an interview to see your progress here.")
        return
    df = pd.DataFrame(rows, columns=["Session", "Date", "Role", "Level", "Avg score", "Fillers", "Avg WPM"])
    c = st.columns(4)
    c[0].metric("Sessions", len(df))
    c[1].metric("Best score", f"{df['Avg score'].max()}/10")
    c[2].metric("Latest score", f"{df['Avg score'].iloc[-1]}/10")
    c[3].metric("Total fillers", int(df["Fillers"].sum()))
    l, r = st.columns(2)
    with l:
        st.markdown("##### 📈 Score trend")
        st.line_chart(df.set_index("Session")["Avg score"])
    with r:
        st.markdown("##### 🗣️ Filler words (lower is better)")
        st.bar_chart(df.set_index("Session")["Fillers"])
    wk = memory.all_weak_counts()
    if wk:
        st.markdown("##### 🎯 Topics to practise")
        st.bar_chart(pd.Series(dict(wk)))
    st.markdown("##### 🗂️ History")
    st.dataframe(df, hide_index=True)
    if st.button("🗑️ Clear all history"):
        memory.clear_history()
        st.rerun()


# ---------------- page ----------------
st.markdown("""<div class='hero'><h1>🎤 AI Interview Coach</h1>
<p>Practise role-specific mock interviews with voice, instant feedback and progress tracking.</p></div>""",
            unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ Interview setup")
    role = st.selectbox("Role", ROLES)
    level = st.selectbox("Level", LEVELS)
    total = st.slider("Number of questions", 2, 8, 4)
    st.checkbox("🔊 Read questions aloud", value=True, key="speak")
    jd = st.text_area("Job description (optional)", height=90,
                      placeholder="Paste the job posting or skills here...")
    resume_file = st.file_uploader("📄 Resume (PDF/TXT, optional)", type=["pdf", "txt"])
    resume_text = read_resume(resume_file)
    if resume_file is not None:
        if resume_text:
            st.caption(f"✅ Resume read ({len(resume_text)} characters)")
        else:
            st.warning("Could not read text from this file. Paste your key skills in the box above.")
    start = st.button("🚀 Start interview", type="primary")
    st.divider()
    st.metric("🔥 Day streak", memory.streak())
    for bdg in memory.badges():
        st.success(bdg)

if not llm.has_key():
    st.error("API key missing. Create a `.env` file next to app.py with "
             "`GEMINI_API_KEY=your_key`, save it and restart the app.")
    st.stop()

if start:
    ctx = (jd.strip() + "\n" + (resume_text or "")).strip()[:4000]
    try:
        with st.spinner("Preparing your personalised questions..."):
            qs = llm.generate_questions(role, level, total, ctx, memory.weak_topics(role))
        S.update(started=True, finished=False, idx=0, questions=qs, audio={}, played=[],
                 results=[], last=None, role=role, level=level, total=len(qs), context=ctx)
        st.rerun()
    except llm.LLMError as e:
        st.error(str(e))

tab1, tab2 = st.tabs(["🎙️ Interview", "📈 Progress"])
with tab1:
    if not S.started:
        welcome_view()
    elif S.finished:
        finish_view()
    else:
        question_view()
with tab2:
    progress_view()