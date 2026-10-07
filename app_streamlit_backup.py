"""
app.py
AI-Based Notes Summarization Assistant — High-Level Clean White Edition
A next-generation study companion that turns messy lecture notes, PDFs, and text
into structured summaries, key takeaways, interactive flashcards, and self-graded quizzes.
"""

import streamlit as st
import json
import importlib
from extractor import extract_text
import ai_engine
importlib.reload(ai_engine)
from ai_engine import generate_study_package, DEMO_PRESETS

# Page configuration
st.set_page_config(
    page_title="NotesGenius AI — Study Assistant",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# High-Level Clean White / Light Theme CSS (Apple & Stripe inspired)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

    /* Global Base Styling: Pure Clean White Theme */
    html, body, [class*="css"], .stApp {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
        background-color: #ffffff !important;
        color: #0f172a !important;
    }

    /* Ambient Subtle Mesh on Clean White */
    .stApp {
        background: 
            radial-gradient(circle at 10% 5%, rgba(99, 102, 241, 0.04) 0%, transparent 40%),
            radial-gradient(circle at 90% 15%, rgba(59, 130, 246, 0.04) 0%, transparent 40%),
            radial-gradient(circle at 50% 95%, rgba(14, 165, 233, 0.03) 0%, transparent 50%),
            #ffffff !important;
    }

    /* Sidebar Clean Styling */
    [data-testid="stSidebar"] {
        background: #f8fafc !important;
        border-right: 1px solid #e2e8f0 !important;
    }

    [data-testid="stSidebar"] .stMarkdown, 
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] span {
        color: #1e293b !important;
    }

    /* Glowing Pill Badge */
    .hero-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 6px 14px;
        background: #eef2ff;
        border: 1px solid #c7d2fe;
        border-radius: 9999px;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: #4338ca;
        margin-bottom: 0.75rem;
        box-shadow: 0 2px 8px rgba(99, 102, 241, 0.08);
    }

    /* Main Title */
    .main-title {
        font-size: 2.6rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 50%, #4f46e5 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.35rem;
        line-height: 1.15;
    }

    .sub-title {
        color: #475569 !important;
        font-size: 1.05rem;
        font-weight: 400;
        margin-bottom: 1.8rem;
    }

    /* High-Level Metric Cards Grid (Clean White) */
    .metrics-container {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 16px;
        margin: 1.5rem 0 2rem 0;
    }

    .clean-metric {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 20px 22px;
        box-shadow: 0 4px 15px -1px rgba(0, 0, 0, 0.04), 0 2px 6px -1px rgba(0, 0, 0, 0.02);
        position: relative;
        overflow: hidden;
        transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
    }

    .clean-metric:hover {
        transform: translateY(-2px);
        border-color: #818cf8;
        box-shadow: 0 12px 25px -4px rgba(99, 102, 241, 0.12);
    }

    .clean-metric::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 3px;
        background: linear-gradient(90deg, #3b82f6, #6366f1);
    }

    .metric-label {
        font-size: 0.74rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #64748b;
        margin-bottom: 6px;
    }

    .metric-num {
        font-size: 2rem;
        font-weight: 800;
        color: #0f172a;
        letter-spacing: -0.02em;
        line-height: 1;
    }

    .metric-sub {
        font-size: 0.83rem;
        color: #64748b;
        margin-top: 5px;
        font-weight: 500;
    }

    .metric-badge-green {
        display: inline-block;
        padding: 3px 8px;
        background: #ecfdf5;
        border: 1px solid #a7f3d0;
        color: #059669;
        border-radius: 9999px;
        font-size: 0.72rem;
        font-weight: 700;
        margin-left: 6px;
    }

    /* Content Cards (Summary & Content) */
    .content-white-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 18px;
        padding: 28px 32px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.03);
        margin-bottom: 24px;
        color: #1e293b;
    }

    .content-white-card h3 {
        color: #1e3a8a !important;
        margin-top: 1.2rem;
        margin-bottom: 0.6rem;
    }

    .content-white-card p, .content-white-card li {
        color: #334155 !important;
        font-size: 1.02rem;
        line-height: 1.7;
    }

    .card-meta-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding-bottom: 14px;
        margin-bottom: 18px;
        border-bottom: 1px solid #f1f5f9;
        font-size: 0.78rem;
        color: #64748b;
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
    }

    /* Flashcard (Clean White & Soft Indigo Shadow) */
    .clean-flashcard {
        background: linear-gradient(145deg, #ffffff 0%, #f8faff 100%);
        border: 2px solid #e0e7ff;
        border-radius: 20px;
        padding: 42px 32px;
        min-height: 240px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        text-align: center;
        box-shadow: 0 12px 30px -4px rgba(99, 102, 241, 0.12), 0 4px 10px -2px rgba(0, 0, 0, 0.03);
        position: relative;
        margin: 20px 0;
        transition: all 0.3s ease;
    }

    .clean-tag {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin-bottom: 16px;
        padding: 5px 14px;
        border-radius: 9999px;
    }

    .tag-question {
        color: #1d4ed8;
        background: #eff6ff;
        border: 1px solid #bfdbfe;
    }

    .tag-answer {
        color: #047857;
        background: #ecfdf5;
        border: 1px solid #a7f3d0;
    }

    .clean-text {
        font-size: 1.45rem;
        font-weight: 600;
        color: #0f172a;
        line-height: 1.45;
        max-width: 800px;
    }

    /* Streamlit Tab Styling (Modern Light Pill Dock) */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: #f1f5f9 !important;
        padding: 6px;
        border-radius: 12px;
        border: 1px solid #e2e8f0 !important;
        margin-bottom: 1.5rem;
    }

    .stTabs [data-baseweb="tab"] {
        padding: 10px 22px;
        border-radius: 8px;
        font-weight: 600;
        font-size: 0.92rem;
        color: #475569 !important;
        border: none !important;
        background: transparent !important;
        transition: all 0.2s ease;
    }

    .stTabs [aria-selected="true"] {
        background: #ffffff !important;
        color: #4338ca !important;
        border: 1px solid #c7d2fe !important;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.06) !important;
    }

    /* Buttons */
    .stButton > button {
        border-radius: 10px;
        font-weight: 600;
        letter-spacing: 0.01em;
        transition: all 0.2s ease;
    }

    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #2563eb 0%, #4f46e5 100%) !important;
        color: #ffffff !important;
        border: none !important;
        box-shadow: 0 4px 14px rgba(37, 99, 235, 0.3) !important;
    }

    .stButton > button[kind="primary"]:hover {
        box-shadow: 0 6px 20px rgba(37, 99, 235, 0.45) !important;
        transform: translateY(-1px);
    }
</style>
""", unsafe_allow_html=True)

# Session state setup
if "package" not in st.session_state:
    st.session_state.package = None
if "raw_notes" not in st.session_state:
    st.session_state.raw_notes = ""
if "current_card" not in st.session_state:
    st.session_state.current_card = 0
if "card_flipped" not in st.session_state:
    st.session_state.card_flipped = False
if "quiz_answers" not in st.session_state:
    st.session_state.quiz_answers = {}
if "quiz_submitted" not in st.session_state:
    st.session_state.quiz_submitted = False


# ---------------- SIDEBAR CONTROLS ----------------
with st.sidebar:
    st.markdown('<div class="hero-badge">⚡ Core Engine</div>', unsafe_allow_html=True)
    st.markdown("### ⚙️ AI Configuration")
    
    provider_options = [
        "Auto-Detect",
        "Groq (Free & Fast)",
        "Demo Mode (Offline / No Key)",
        "Google Gemini",
        "Anthropic Claude",
        "OpenAI"
    ]
    provider_selection = st.selectbox("LLM Provider", provider_options, index=0)
    provider_clean = provider_selection.split(" (")[0]
    
    api_key_input = ""
    if provider_clean not in ["Demo Mode", "Demo Mode (Offline / No Key)"]:
        api_key_input = st.text_input(
            f"{provider_clean} API Key",
            type="password",
            placeholder="Paste key or leave blank for env",
            help="Leave blank to use environment variable or auto-detect."
        )

    st.markdown("---")
    st.markdown("### 📥 Source Ingestion")

    # 1-Click Samples for Judges
    st.caption("**⚡ 1-Click Demo Samples (For Instant Pitch):**")
    col_demo1, col_demo2 = st.columns(2)
    with col_demo1:
        if st.button("💻 OS & Systems", use_container_width=True):
            st.session_state.raw_notes = (
                "Operating Systems: Concurrency, Deadlocks, and Semaphores.\n"
                "A race condition arises when multiple processes read and write shared data concurrently "
                "and the outcome depends on the particular order of execution. Critical Section problem "
                "requires Mutual Exclusion, Progress, and Bounded Waiting.\n"
                "Semaphores provide wait() (P) and signal() (V) operations. Mutex locks are binary semaphores.\n"
                "Deadlocks occur when four Coffman conditions hold: Mutual Exclusion, Hold and Wait, "
                "No Preemption, and Circular Wait. Banker's Algorithm avoids deadlock by safe state checking."
            )
            st.rerun()

    with col_demo2:
        if st.button("🧬 Bio Energetics", use_container_width=True):
            st.session_state.raw_notes = (
                "Cellular Energetics: Photosynthesis and Cellular Respiration.\n"
                "Photosynthesis equation: 6CO2 + 6H2O + light -> C6H12O6 + 6O2. Occurs in chloroplasts.\n"
                "Light-dependent reactions take place in the thylakoid membranes, generating ATP and NADPH.\n"
                "The Calvin cycle fixes CO2 into sugars in the stroma.\n"
                "Cellular respiration breaks down glucose in four stages: Glycolysis (cytosol, 2 net ATP), "
                "Pyruvate Oxidation, Krebs Cycle (mitochondrial matrix), and Electron Transport Chain (inner membrane). "
                "Oxidative phosphorylation generates 28-32 ATP via ATP synthase and oxygen as terminal electron acceptor."
            )
            st.rerun()

    input_mode = st.radio("Input format", ["Upload Document (PDF / Image / TXT)", "Paste Text"])
    
    uploaded_file = None
    if input_mode == "Upload Document (PDF / Image / TXT)":
        uploaded_file = st.file_uploader(
            "Upload lecture notes",
            type=["pdf", "txt", "md", "png", "jpg", "jpeg", "webp"],
            help="Supports PDFs, text notes, and photos of paper/whiteboard notes."
        )
    else:
        st.session_state.raw_notes = st.text_area(
            "Lecture text or transcript:",
            value=st.session_state.raw_notes,
            height=200,
            placeholder="Type or paste messy notes here..."
        )

    st.markdown("---")
    generate_btn = st.button("✨ Synthesize Study Pack", type="primary", use_container_width=True)

    if st.session_state.package:
        if st.button("🔄 Reset Workspace", use_container_width=True):
            st.session_state.package = None
            st.session_state.raw_notes = ""
            st.session_state.quiz_answers = {}
            st.session_state.quiz_submitted = False
            st.session_state.current_card = 0
            st.rerun()


# ---------------- ACTION: GENERATION ----------------
if generate_btn:
    st.session_state.quiz_answers = {}
    st.session_state.quiz_submitted = False
    st.session_state.current_card = 0
    st.session_state.card_flipped = False

    text_to_process = ""
    try:
        if input_mode == "Upload Document (PDF / Image / TXT)":
            if uploaded_file is None:
                st.sidebar.error("⚠️ Please select a file to upload first.")
                st.stop()
            with st.spinner("📄 Extracting text layers and document structures..."):
                text_to_process = extract_text(uploaded_file.name, uploaded_file.getvalue())
                st.session_state.raw_notes = text_to_process
        else:
            text_to_process = st.session_state.raw_notes.strip()
            if not text_to_process:
                st.sidebar.error("⚠️ Please paste notes or click one of the 1-Click Demo Samples.")
                st.stop()

        with st.spinner("🤖 Neural engine synthesizing summary, flashcards & active-recall quiz..."):
            pkg = generate_study_package(
                notes_text=text_to_process,
                provider=provider_clean,
                api_key=api_key_input,
                model=""
            )
            st.session_state.package = pkg
            st.success("Study Pack successfully generated!")
            st.rerun()

    except Exception as e:
        st.sidebar.error(f"Error: {e}")
        st.sidebar.info("Tip: You can switch provider to 'Demo Mode' for an immediate offline demo!")


# ---------------- MAIN UI DASHBOARD ----------------
st.markdown('<div class="hero-badge">⚡ AI-Powered Notes Assistant</div>', unsafe_allow_html=True)
st.markdown('<div class="main-title">🎓 AI Notes Summarization Assistant</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Transform messy lecture notes into structured summaries, key insights, interactive flashcards, and quizzes.</div>', unsafe_allow_html=True)

package = st.session_state.package

if package is None:
    # High-Level Clean White Hero
    st.markdown("""
    <div class="content-white-card">
        <div class="card-meta-bar">
            <span>🚀 READY FOR INGESTION</span>
            <span>FORMATS: PDF • OCR • TEXT • MARKDOWN</span>
        </div>
        <h3 style="margin-top:0;">Transform Any Lecture In Seconds</h3>
        <p>
            Select a <b>1-Click Demo Sample</b> or upload your lecture PDF from the sidebar to generate a complete active-recall study suite.
        </p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown("""
        <div class="clean-metric">
            <div class="metric-label">📝 RECURSIVE SUMMARY</div>
            <div class="metric-num">Structured</div>
            <div class="metric-sub">Distills core conceptual logic</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class="clean-metric">
            <div class="metric-label">🎯 HIGH YIELD</div>
            <div class="metric-num">Key Points</div>
            <div class="metric-sub">Critical exam formulas & theorems</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown("""
        <div class="clean-metric">
            <div class="metric-label">🗂️ ACTIVE RECALL</div>
            <div class="metric-num">Flashcards</div>
            <div class="metric-sub">Interactive 3D-flip term cards</div>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown("""
        <div class="clean-metric">
            <div class="metric-label">🧠 SELF-EVALUATION</div>
            <div class="metric-num">Quiz Arena</div>
            <div class="metric-sub">Auto-graded with explanations</div>
        </div>
        """, unsafe_allow_html=True)

else:
    # Title & Metadata
    title_text = package.get("title", "Generated Study Package")
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:10px; margin-bottom:12px;">
        <span style="font-size:1.8rem;">📌</span>
        <h2 style="margin:0; font-weight:700; color:#0f172a;">{title_text}</h2>
    </div>
    """, unsafe_allow_html=True)

    raw_word_count = len(st.session_state.raw_notes.split()) if st.session_state.raw_notes else 0
    summary_word_count = len(package.get("summary", "").split())
    compression = round((1 - (summary_word_count / max(raw_word_count, 1))) * 100) if raw_word_count > summary_word_count else 0
    cards_count = len(package.get("flashcards", []))
    quiz_count = len(package.get("quiz", []))

    # High-Level Clean Metric Cards Grid
    comp_badge = f'<span class="metric-badge-green">↓ {compression}% Reduction</span>' if compression > 0 else ''
    st.markdown(f"""
    <div class="metrics-container">
        <div class="clean-metric">
            <div class="metric-label">📄 SOURCE SCOPE</div>
            <div class="metric-num">{raw_word_count}</div>
            <div class="metric-sub">Extracted raw words</div>
        </div>
        <div class="clean-metric">
            <div class="metric-label">⚡ AI SYNTHESIS {comp_badge}</div>
            <div class="metric-num">{summary_word_count}</div>
            <div class="metric-sub">Concise study words</div>
        </div>
        <div class="clean-metric">
            <div class="metric-label">🗂️ ACTIVE FLASHCARDS</div>
            <div class="metric-num">{cards_count}</div>
            <div class="metric-sub">Ready for memorization</div>
        </div>
        <div class="clean-metric">
            <div class="metric-label">🧠 EVALUATION QUIZ</div>
            <div class="metric-num">{quiz_count}</div>
            <div class="metric-sub">Auto-graded questions</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # High-Level Navigation Tabs
    tab_summary, tab_points, tab_flash, tab_quiz, tab_export = st.tabs([
        "📝 Conceptual Summary",
        "🎯 High-Yield Takeaways",
        "🗂️ Interactive Flashcards",
        "🧠 Assessment Quiz",
        "💾 Export & Share"
    ])

    # 1. Summary Tab
    with tab_summary:
        read_time = max(1, round(summary_word_count / 200))
        st.markdown(f"""
        <div class="content-white-card">
            <div class="card-meta-bar">
                <span>⏱️ ESTIMATED READ: ~{read_time} MIN</span>
                <span>STATUS: EXAM RECAP READY</span>
                <span>RETENTION METHOD: CONCEPTUAL DRILLDOWN</span>
            </div>
        """, unsafe_allow_html=True)

        st.markdown(package.get("summary", "No summary available."))
        st.markdown("</div>", unsafe_allow_html=True)

    # 2. Key Points Tab
    with tab_points:
        st.markdown("""
        <div class="content-white-card">
            <div class="card-meta-bar">
                <span>🎯 CORE HIGH-YIELD THEOREMS & PRINCIPLES</span>
            </div>
        """, unsafe_allow_html=True)

        key_points = package.get("key_points", [])
        if key_points:
            for i, pt in enumerate(key_points):
                st.markdown(f"**{i+1}.** {pt}")
        else:
            st.info("No key points generated.")
        st.markdown("</div>", unsafe_allow_html=True)

    # 3. Flashcards Tab
    with tab_flash:
        flashcards = package.get("flashcards", [])
        if flashcards:
            total_cards = len(flashcards)
            curr = st.session_state.current_card % total_cards
            card = flashcards[curr]

            is_flipped = st.session_state.card_flipped
            card_content = card.get("back", "") if is_flipped else card.get("front", "")
            tag_class = "tag-answer" if is_flipped else "tag-question"
            tag_text = "💡 SOLUTION / DEFINITION" if is_flipped else "❓ CONCEPT / QUESTION"

            st.markdown(f"""
            <div class="clean-flashcard">
                <div class="clean-tag {tag_class}">{tag_text} • CARD {curr + 1} OF {total_cards}</div>
                <div class="clean-text">{card_content}</div>
                <div style="font-size:0.83rem; color:#64748b; margin-top:20px; font-weight:500;">
                    Click Flip Card below to toggle active recall
                </div>
            </div>
            """, unsafe_allow_html=True)

            fc1, fc2, fc3 = st.columns([1, 1.2, 1])
            with fc1:
                if st.button("⬅️ Previous", use_container_width=True):
                    st.session_state.current_card = (curr - 1) % total_cards
                    st.session_state.card_flipped = False
                    st.rerun()

            with fc2:
                flip_label = "🔄 Flip to Question" if is_flipped else "🔄 Reveal Answer"
                if st.button(flip_label, type="primary", use_container_width=True):
                    st.session_state.card_flipped = not is_flipped
                    st.rerun()

            with fc3:
                if st.button("Next Card ➡️", use_container_width=True):
                    st.session_state.current_card = (curr + 1) % total_cards
                    st.session_state.card_flipped = False
                    st.rerun()

            with st.expander("🔍 Browse All Study Flashcards"):
                for idx, c in enumerate(flashcards):
                    st.markdown(f"**Card {idx+1}:** `{c.get('front')}` ➔ {c.get('back')}")
        else:
            st.info("No flashcards found.")

    # 4. Interactive Quiz Tab
    with tab_quiz:
        quiz = package.get("quiz", [])
        if quiz:
            st.markdown("""
            <div class="card-meta-bar" style="margin-bottom:15px;">
                <span>🧠 SELF-GRADED COMPREHENSION ARENA</span>
                <span>SUBMIT ANSWERS TO BENCHMARK KNOWLEDGE</span>
            </div>
            """, unsafe_allow_html=True)

            for i, q in enumerate(quiz):
                q_key = f"quiz_q_{i}"
                st.markdown(f"##### **Question {i + 1}:** {q.get('question')}")
                opts = q.get("options", [])

                st.session_state.quiz_answers[q_key] = st.radio(
                    label=f"Options for question {i+1}",
                    options=list(range(len(opts))),
                    format_func=lambda idx, options=opts: options[idx],
                    key=q_key,
                    index=st.session_state.quiz_answers.get(q_key, None),
                    label_visibility="collapsed"
                )
                st.write("")

            col_submit, _ = st.columns([1.2, 2])
            with col_submit:
                if st.button("📊 Evaluate & Grade Quiz", type="primary", use_container_width=True):
                    st.session_state.quiz_submitted = True

            if st.session_state.quiz_submitted:
                st.markdown("---")
                score = 0
                for i, q in enumerate(quiz):
                    q_key = f"quiz_q_{i}"
                    chosen = st.session_state.quiz_answers.get(q_key)
                    correct = q.get("correct_index", 0)
                    opts = q.get("options", [])
                    explanation = q.get("explanation", "")

                    if chosen == correct:
                        score += 1
                        st.success(f"✅ **Question {i + 1}: Correct!**\n\n_{explanation}_")
                    else:
                        chosen_text = opts[chosen] if chosen is not None else "No option selected"
                        correct_text = opts[correct] if correct < len(opts) else "Correct Option"
                        st.error(
                            f"❌ **Question {i + 1}: Incorrect.**\n\n"
                            f"- **Your Answer:** {chosen_text}\n"
                            f"- **Correct Answer:** {correct_text}\n"
                            f"- **Explanation:** _{explanation}_"
                        )

                pct = int((score / len(quiz)) * 100)
                st.markdown(f"### 🏆 Evaluation Result: **{score} / {len(quiz)}** ({pct}%)")
                if pct == 100:
                    st.balloons()
                    st.success("🎉 Perfect Score! Flawless conceptual mastery!")
                elif pct >= 66:
                    st.info("👍 Strong comprehension! Review flagged questions to polish edge cases.")
                else:
                    st.warning("📚 Recommended: Review the summary and flashcard definitions before retrying.")
        else:
            st.info("No quiz questions generated.")

    # 5. Export Tab
    with tab_export:
        st.markdown("### 💾 Export Full Study Pack")
        st.caption("Download the synthesized study pack for offline review, printing, or LMS import.")

        export_md = f"# {package.get('title', 'Study Pack')}\n\n"
        export_md += f"## Conceptual Summary\n\n{package.get('summary', '')}\n\n"
        export_md += "## High-Yield Takeaways\n\n"
        for pt in package.get("key_points", []):
            export_md += f"- {pt}\n"
        export_md += "\n## Active Recall Flashcards\n\n"
        for fc in package.get("flashcards", []):
            export_md += f"- **Q:** {fc.get('front')}\n  - **A:** {fc.get('back')}\n"
        export_md += "\n## Practice Evaluation Quiz\n\n"
        for i, q in enumerate(package.get("quiz", [])):
            export_md += f"### Q{i+1}: {q.get('question')}\n"
            for opt in q.get("options", []):
                export_md += f"- [ ] {opt}\n"
            export_md += f"**Answer:** {q.get('options', [''])[q.get('correct_index', 0)]}\n"
            export_md += f"**Explanation:** {q.get('explanation', '')}\n\n"

        exp_col1, exp_col2 = st.columns(2)
        with exp_col1:
            st.download_button(
                label="📥 Download as Markdown (.md)",
                data=export_md,
                file_name="study_pack.md",
                mime="text/markdown",
                use_container_width=True
            )
        with exp_col2:
            st.download_button(
                label="📥 Download as JSON (.json)",
                data=json.dumps(package, indent=2),
                file_name="study_pack.json",
                mime="application/json",
                use_container_width=True
            )
