"""
ai_engine.py
Wraps calls to LLM APIs (Groq, Anthropic, OpenAI, Google Gemini) and provides
an instant offline Demo Mode for reliable hackathon presentations.
Everything returns a structured dict matching:
{
  "title": str,
  "summary": str,
  "key_points": list[str],
  "flashcards": list[dict[front, back]],
  "quiz": list[dict[question, options, correct_index, explanation]]
}
"""

import os
import json
import re
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """You are an expert academic study-pack generator. Your job is NOT to make the notes as short as possible. Your primary objective is INFORMATION COVERAGE: preserve the important knowledge from the source while removing repetition and noise.

SOURCE FIDELITY
- Use ONLY information supported by the supplied notes.
- Do not invent facts, examples, terminology, formulas, definitions, dates, or conclusions.
- Preserve the source's technical terminology and meaning.
- Ignore obvious document metadata such as course codes, page numbers, file names, slide numbers, headers/footers, unless the notes explicitly explain them as content.
- If OCR contains a visibly corrupted token, use surrounding context only to normalize obvious formatting; do not guess missing factual content.
- Never turn a random course code, title fragment, or metadata line into a concept, quiz question, or flashcard.

COVERAGE-FIRST SUMMARIZATION
- First mentally identify ALL meaningful concepts in the source: definitions, properties, rules, classifications, steps/processes, formulas, syntax/code, examples, comparisons, exceptions, conditions, and cause/effect relationships.
- Then compress the wording while preserving those concepts.
- Never delete an important concept merely to satisfy a word target.
- Remove repetition, filler, greetings, duplicated OCR fragments, and unnecessary prose.
- For a source around 600 words, the normal summary target is approximately 250-350 words. This is a target, NOT a hard limit.
- Shorter is acceptable only when the source itself contains little meaningful information.
- Longer is acceptable when needed to preserve important content.
- Prefer headings and bullets for dense technical material.

OUTPUT QUALITY
- The summary must be useful for exam revision, not merely a paraphrase.
- Key points must cover distinct concepts, not repeat the same idea.
- Flashcards must test/define distinct concepts found in the source.
- Quiz questions must test different concepts and must not repeat the same question pattern.
- Every quiz option must be plausible and relevant to the same topic.
- Wrong options must not be absurd generic statements unrelated to the source.
- Exactly one option must be correct.
- Explanations must be supported by the source.
- Avoid duplicate or near-duplicate questions/cards.

ADAPTIVE COUNTS
- key_points: usually 6-12, depending on source coverage.
- flashcards: usually 6-12, depending on number of distinct concepts.
- quiz: usually 5-10, depending on source coverage. For very short notes, use fewer.
- Do not manufacture extra items just to hit a number.

Return ONLY one valid JSON object:
{
  "title": "Short descriptive title",
  "summary": "Markdown study summary",
  "key_points": ["distinct point 1", "..."],
  "flashcards": [
    {"front": "Question or key term", "back": "Answer/definition"}
  ],
  "quiz": [
    {
      "question": "Distinct source-grounded question",
      "options": ["A", "B", "C", "D"],
      "correct_index": 0,
      "explanation": "Source-grounded explanation"
    }
  ]
}
"""
# Sample offline presets for foolproof hackathon demos
DEMO_PRESETS = {
    "Operating Systems": {
        "title": "Operating Systems: Concurrency & Process Synchronization",
        "summary": (
            "### 📌 Process Synchronization & Race Conditions\n\n"
            "Process synchronization coordinates concurrent execution when multiple processes or threads share resources or memory. "
            "When threads access shared variables without synchronization, a **race condition** occurs, corrupting data integrity.\n\n"
            "### ⚙️ The Critical Section Problem\n\n"
            "A proper synchronization protocol must satisfy three core conditions:\n"
            "- **Mutual Exclusion**: Only one process can execute inside the critical section at any given moment.\n"
            "- **Progress**: The decision on who enters next cannot be postponed indefinitely if the critical section is free.\n"
            "- **Bounded Waiting**: There must be a ceiling on how many times other processes can enter before a waiting process is admitted.\n\n"
            "### 🔒 Semaphores & Deadlock Avoidance\n\n"
            "**Semaphores** regulate access using atomic operations: `wait()` ($P$) and `signal()` ($V$). "
            "Deadlocks arise when all four **Coffman conditions** hold simultaneously: Mutual Exclusion, Hold and Wait, No Preemption, and Circular Wait."
        ),
        "key_points": [
            "Race conditions happen when output depends on non-deterministic thread execution order.",
            "The Critical Section requires Mutual Exclusion, Progress, and Bounded Waiting.",
            "Semaphores provide atomic wait() (P) and signal() (V) operations.",
            "Four deadlock conditions (Coffman): Mutual Exclusion, Hold & Wait, No Preemption, Circular Wait.",
            "Banker's Algorithm and Resource Allocation Graphs are used to detect and avoid deadlocks."
        ],
        "flashcards": [
            {"front": "Race Condition", "back": "A flaw where output depends on non-deterministic timing/sequence of threads."},
            {"front": "Mutual Exclusion", "back": "Only one process can execute in its critical section at any given instant."},
            {"front": "Counting Semaphore", "back": "A synchronization tool whose integer value can range over an unrestricted domain."},
            {"front": "Coffman Conditions", "back": "The four required conditions for deadlock: Mutual Exclusion, Hold & Wait, No Preemption, Circular Wait."},
            {"front": "Banker's Algorithm", "back": "A deadlock avoidance algorithm that simulates resource allocation to check for safe states."}
        ],
        "quiz": [
            {
                "question": "Which condition is NOT one of the Coffman conditions required for a deadlock?",
                "options": ["Mutual Exclusion", "Circular Wait", "Preemptive Scheduling", "Hold and Wait"],
                "correct_index": 2,
                "explanation": "No Preemption (not Preemptive Scheduling) is required for deadlock; resources cannot be forcibly seized."
            },
            {
                "question": "What happens when a process invokes wait() (or P()) on a counting semaphore with value 0?",
                "options": ["The semaphore increments to 1", "The process blocks until another process calls signal()", "An exception is raised", "The process terminates immediately"],
                "correct_index": 1,
                "explanation": "wait() blocks the calling process if the semaphore count is less than or equal to 0."
            },
            {
                "question": "Which criteria guarantees that a process will eventually get to enter its critical section without starving?",
                "options": ["Mutual Exclusion", "Bounded Waiting", "Resource Isolation", "Strict Alternation"],
                "correct_index": 1,
                "explanation": "Bounded Waiting ensures a ceiling on how many times others can enter before a waiting process is admitted."
            }
        ]
    },
    "Cellular Biology": {
        "title": "Cellular Biology: Photosynthesis & Cellular Respiration",
        "summary": (
            "### 🌿 Photosynthesis: Harnessing Light Energy\n\n"
            "Photosynthesis converts light energy into chemical energy stored in glucose within chloroplasts. "
            "It consists of light-dependent reactions in the **thylakoid membrane** (producing ATP & NADPH) "
            "and the light-independent **Calvin cycle** in the stroma (fixing CO2 into sugars).\n\n"
            "### ⚡ Cellular Respiration: ATP Production\n\n"
            "Cellular respiration breaks down glucose in four stages:\n"
            "- **Glycolysis**: Cytoplasmic breakdown yielding net 2 ATP, 2 NADH, and 2 Pyruvate.\n"
            "- **Pyruvate Oxidation & Krebs Cycle**: In the mitochondrial matrix, producing electron carriers (NADH, FADH2).\n"
            "- **Oxidative Phosphorylation**: In the inner membrane, producing 28-32 ATP via the Electron Transport Chain and ATP Synthase.\n\n"
            "### 🔄 The Biological Energy Loop\n\n"
            "Together, these pathways drive the global carbon cycle: the products of photosynthesis (glucose and O2) "
            "serve as reactants for respiration, while respiration yields CO2 and water."
        ),
        "key_points": [
            "Photosynthesis formula: 6 CO2 + 6 H2O + Light -> C6H12O6 + 6 O2.",
            "Light reactions split water, generating ATP and NADPH while releasing O2 as a byproduct.",
            "Calvin cycle fixes atmospheric CO2 into G3P using ATP and NADPH.",
            "Glycolysis yields a net of 2 ATP, 2 NADH, and 2 Pyruvate per glucose molecule without needing oxygen.",
            "Oxidative phosphorylation generates the majority of ATP (~28-32 ATP) via chemiosmosis and ATP synthase."
        ],
        "flashcards": [
            {"front": "ATP Synthase", "back": "Enzyme that harnesses proton gradient energy across the inner mitochondrial membrane to synthesize ATP."},
            {"front": "Thylakoid Membrane", "back": "Site of the light-dependent reactions of photosynthesis inside chloroplasts."},
            {"front": "Glycolysis", "back": "Anaerobic cytoplasmic breakdown of 1 glucose molecule into 2 pyruvate molecules."},
            {"front": "Chemiosmosis", "back": "The movement of hydrogen ions down their electrochemical gradient to drive cellular work."}
        ],
        "quiz": [
            {
                "question": "Where does the Calvin Cycle occur inside a plant cell?",
                "options": ["Thylakoid lumen", "Stroma of the chloroplast", "Mitochondrial matrix", "Cytoplasm"],
                "correct_index": 1,
                "explanation": "The Calvin cycle takes place in the fluid stroma surrounding thylakoids."
            },
            {
                "question": "What is the net yield of ATP produced directly during Glycolysis per glucose molecule?",
                "options": ["4 ATP", "2 ATP", "32 ATP", "1 ATP"],
                "correct_index": 1,
                "explanation": "Glycolysis consumes 2 ATP and produces 4 ATP, resulting in a net yield of 2 ATP."
            },
            {
                "question": "What is the primary terminal electron acceptor in the aerobic Electron Transport Chain?",
                "options": ["NAD+", "Oxygen (O2)", "Carbon dioxide (CO2)", "Water (H2O)"],
                "correct_index": 1,
                "explanation": "Molecular oxygen binds electrons and protons at complex IV to form water."
            }
        ]
    }
}

def _normalize_notes(notes_text: str) -> str:
    """Lightly clean extraction/OCR noise without changing the source meaning."""
    text = notes_text.replace("\x00", " ")
    text = text.replace("\ufffd", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove obvious repeated whitespace while preserving line structure.
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Remove repeated identical lines commonly caused by PDF/OCR extraction.
    lines = []
    previous = None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            if lines and lines[-1] != "":
                lines.append("")
            continue
        if stripped == previous:
            continue
        lines.append(stripped)
        previous = stripped

    return "\n".join(lines).strip()


def _summary_target(word_count: int) -> str:
    if word_count <= 250:
        return "approximately 40-60% of the source length"
    if word_count <= 700:
        return "approximately 40-60% of the source length (for ~600 words, usually 250-350 words)"
    if word_count <= 1500:
        return "approximately 35-55% of the source length"
    return "a compact hierarchical summary; prioritize complete concept coverage over aggressive compression"


def _build_user_prompt(notes_text: str) -> str:
    word_count = len(notes_text.split())
    return f"""Create a study package from the following source notes.

SOURCE WORD COUNT: {word_count}
SUMMARY TARGET: {_summary_target(word_count)}

Before writing the final JSON, internally:
1. Identify distinct concepts and important supporting details.
2. Separate actual subject content from metadata/OCR noise.
3. Make sure the summary covers the identified concepts.
4. Build key points, flashcards, and quiz questions from those same concepts.
5. Check that quiz questions are not duplicates and that each has exactly one defensible answer.

IMPORTANT: Do not optimize for maximum word reduction. Optimize for retention and coverage.

SOURCE NOTES
----------------
{notes_text[:60000]}
----------------
"""


def _validate_package(data: dict) -> dict:
    """Normalize the model result and remove obvious structural problems."""
    if not isinstance(data, dict):
        raise ValueError("Model did not return an object.")

    data.setdefault("title", "Generated Study Package")
    data.setdefault("summary", "")
    data.setdefault("key_points", [])
    data.setdefault("flashcards", [])
    data.setdefault("quiz", [])

    if not isinstance(data["key_points"], list):
        data["key_points"] = []
    if not isinstance(data["flashcards"], list):
        data["flashcards"] = []
    if not isinstance(data["quiz"], list):
        data["quiz"] = []

    # Keep only usable key points.
    points = []
    seen_points = set()
    for p in data["key_points"]:
        p = str(p).strip()
        key = re.sub(r"\W+", " ", p.lower()).strip()
        if p and key and key not in seen_points:
            seen_points.add(key)
            points.append(p)
    data["key_points"] = points

    # Normalize flashcards and remove exact duplicates.
    cards = []
    seen_cards = set()
    for c in data["flashcards"]:
        if not isinstance(c, dict):
            continue
        front = str(c.get("front", "")).strip()
        back = str(c.get("back", "")).strip()
        key = (re.sub(r"\W+", " ", front.lower()).strip(),
               re.sub(r"\W+", " ", back.lower()).strip())
        if front and back and key not in seen_cards:
            seen_cards.add(key)
            cards.append({"front": front, "back": back})
    data["flashcards"] = cards

    # Normalize quiz objects and reject duplicate questions.
    quiz = []
    seen_questions = set()
    for q in data["quiz"]:
        if not isinstance(q, dict):
            continue
        question = str(q.get("question", "")).strip()
        options = q.get("options", [])
        explanation = str(q.get("explanation", "")).strip()
        try:
            correct = int(q.get("correct_index", 0))
        except (TypeError, ValueError):
            correct = 0

        if not question or not isinstance(options, list) or len(options) != 4:
            continue

        options = [str(o).strip() for o in options]
        normalized_q = re.sub(r"\W+", " ", question.lower()).strip()
        normalized_options = [re.sub(r"\W+", " ", o.lower()).strip() for o in options]

        if (not all(options) or len(set(normalized_options)) != 4 or
                correct < 0 or correct >= 4 or normalized_q in seen_questions):
            continue

        seen_questions.add(normalized_q)
        quiz.append({
            "question": question,
            "options": options,
            "correct_index": correct,
            "explanation": explanation
        })

    data["quiz"] = quiz
    return data


def _clean_json_response(raw_text: str) -> dict:
    """Robustly extract and parse JSON from model output."""
    raw_text = raw_text.strip()
    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
    raw_text = re.sub(r"\s*```$", "", raw_text)

    match = re.search(r"\{[\s\S]*\}", raw_text)
    if match:
        raw_text = match.group(0)

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Model response was not valid JSON: {raw_text[:300]}...") from e

    return _validate_package(data)


def _generate_with_groq(notes_text: str, api_key: str, model: str = "") -> dict:
    from groq import Groq
    client = Groq(api_key=api_key)

    try:
        live_models_resp = client.models.list()
        live_ids = [m.id for m in live_models_resp.data]
    except Exception:
        live_ids = []

    preferred = [
        "openai/gpt-oss-20b",
        "llama-3.3-70b-versatile",
        "llama-3.1-70b-versatile",
        "llama-3.1-8b-instant",
        "gemma2-9b-it",
    ]

    if model:
        preferred = [model] + preferred

    candidates = [m for m in preferred if not live_ids or m in live_ids]
    if not candidates:
        candidates = live_ids

    last_error = None
    for cand in candidates:
        if any(skip in cand.lower() for skip in ["whisper", "guard", "orpheus", "tts"]):
            continue

        for use_json in [True, False]:
            try:
                kwargs = dict(
                    model=cand,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": _build_user_prompt(notes_text)}
                    ],
                    temperature=0.15,
                    max_tokens=6000,
                )
                if use_json:
                    kwargs["response_format"] = {"type": "json_object"}

                response = client.chat.completions.create(**kwargs)
                return _clean_json_response(response.choices[0].message.content)

            except Exception as e:
                last_error = e
                err_msg = str(e).lower()
                if any(k in err_msg for k in ["decommission", "not found", "does not exist",
                                              "no longer", "deprecated", "404", "model"]):
                    break
                if "response_format" in err_msg or "json" in err_msg:
                    continue
                raise

    raise ValueError(f"Groq generation failed: {last_error}")


def _generate_with_anthropic(notes_text: str, api_key: str,
                             model: str = "claude-3-5-haiku-20241022") -> dict:
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=6000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _build_user_prompt(notes_text)}],
    )
    raw_text = "".join(b.text for b in response.content if b.type == "text")
    return _clean_json_response(raw_text)


def _generate_with_openai(
    notes_text: str,
    api_key: str,
    model: str = "openrouter/free"
) -> dict:
    from openai import OpenAI

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": _build_user_prompt(notes_text)
            }
        ],
        temperature=0.15,
        response_format={"type": "json_object"},
        max_tokens=6000,
    )

    return _clean_json_response(
        response.choices[0].message.content
    )

def _generate_with_gemini(notes_text: str, api_key: str,
                          model: str = "gemini-1.5-flash") -> dict:
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    gemini_model = genai.GenerativeModel(
        model_name=model,
        system_instruction=SYSTEM_PROMPT,
        generation_config={
            "response_mime_type": "application/json",
            "temperature": 0.15,
            "max_output_tokens": 6000,
        }
    )
    response = gemini_model.generate_content(_build_user_prompt(notes_text))
    return _clean_json_response(response.text)


def _generate_fallback_demo(notes_text: str) -> dict:
    """High-quality offline fallback that still respects the uploaded notes."""
    lower = notes_text.lower()

    # Existing curated demo topics.
    if "photosynthesis" in lower or "respiration" in lower or "cellular biology" in lower:
        return DEMO_PRESETS["Cellular Biology"]

    if "deadlock" in lower or "semaphore" in lower or "operating system" in lower:
        return DEMO_PRESETS["Operating Systems"]

    # OOP-specific offline demo/fallback: prevents generic nonsense questions.
    if any(term in lower for term in [
        "object oriented", "object-oriented", "class", "encapsulation",
        "inheritance", "polymorphism", "abstraction", "variable", "data type"
    ]):
        return {
            "title": "Object-Oriented Programming: Core Concepts",
            "summary": (
                "### 📌 Fundamental Concepts & Overview\n\n"
                "Object-Oriented Programming (OOP) organizes software around objects and the data and behavior associated with them. "
                "A variable is a named memory location used to store data that can change during program execution. "
                "Each variable has a data type, a name (identifier), and a value.\n\n"
                "### 🔍 Core Principles & Properties\n\n"
                "- **Variables** store values and are associated with a specific **data type** and identifier.\n"
                "- Common data types mentioned in the notes include **int**, **double**, and **char**.\n"
                "- A variable's value can change during program execution.\n\n"
                "### 🚀 Practical Examples\n\n"
                "- `int age = 20;` demonstrates an integer variable.\n"
                "- `double salary = 50000.50;` demonstrates a double variable.\n"
            ),
            "key_points": [
                "A variable is a named memory location used to store data that can change during execution.",
                "Each variable has a data type, name (identifier), and value.",
                "int, double, and char are examples of data types.",
                "Example: double salary = 50000.50;",
                "Example: age, salary, and grade can be variables."
            ],
            "flashcards": [
                {"front": "What is a variable?", "back": "A named memory location used to store data that can change during program execution."},
                {"front": "What three things characterize a variable?", "back": "A data type, a name (identifier), and a value."},
                {"front": "Name three data types mentioned in the notes.", "back": "int, double, and char."},
                {"front": "What does `double salary = 50000.50;` demonstrate?", "back": "A double variable named salary initialized with the value 50000.50."},
                {"front": "Give examples of variables.", "back": "age, salary, and grade are examples of variables mentioned in the notes."}
            ],
            "quiz": [
                {
                    "question": "What is a variable?",
                    "options": [
                        "A named memory location used to store data",
                        "A programming language",
                        "A loop that repeats forever",
                        "A hardware device"
                    ],
                    "correct_index": 0,
                    "explanation": "The notes define a variable as a named memory location used to store data that can change during execution."
                },
                {
                    "question": "Which set contains data types mentioned in the notes?",
                    "options": [
                        "int, double, char",
                        "age, salary, grade",
                        "class, object, method",
                        "read, write, execute"
                    ],
                    "correct_index": 0,
                    "explanation": "The notes specifically identify int, double, and char as data types."
                },
                {
                    "question": "In `double salary = 50000.50;`, what is `salary`?",
                    "options": [
                        "A variable/identifier",
                        "A data type",
                        "A character literal",
                        "A class name"
                    ],
                    "correct_index": 0,
                    "explanation": "The notes use salary as an example of a variable; double is the data type."
                }
            ]
        }

    # Generic deterministic fallback: use source sentences rather than inventing facts.
    normalized = _normalize_notes(notes_text)
    sentences = [
        s.strip(" -*•\t")
        for s in re.split(r"(?<=[.!?])\s+|\n+", normalized)
        if len(s.strip()) >= 20
    ]

    # Remove near-duplicate sentences.
    unique = []
    seen = set()
    for s in sentences:
        key = re.sub(r"\W+", " ", s.lower()).strip()
        if key and key not in seen:
            seen.add(key)
            unique.append(s)

    if not unique:
        unique = ["The uploaded notes did not contain enough readable text to build a study package."]

    title_words = unique[0].split()[:7]
    title = " ".join(title_words).strip(" .,:;") or "Study Notes"

    summary_sentences = unique[:min(10, len(unique))]
    summary = "### 📌 Fundamental Concepts & Overview\n\n" + "\n\n".join(summary_sentences)

    key_points = unique[:min(10, len(unique))]

    flashcards = [
        {"front": f"What does this note state? (Concept {i+1})", "back": s}
        for i, s in enumerate(unique[:min(8, len(unique))])
    ]

    quiz = []
    for i, s in enumerate(unique[:min(5, len(unique))]):
        quiz.append({
            "question": f"Which statement is directly supported by the source notes?",
            "options": [
                s[:180],
                "The source does not provide this information.",
                "The source states the opposite of this.",
                "The source gives no relevant information about the topic."
            ],
            "correct_index": 0,
            "explanation": f"This option is directly supported by the uploaded notes: {s}"
        })

    return _validate_package({
        "title": f"Study Pack: {title}",
        "summary": summary,
        "key_points": key_points,
        "flashcards": flashcards,
        "quiz": quiz
    })


def generate_study_package(
    notes_text: str,
    provider: str = "Auto-Detect",
    api_key: str = "",
    model: str = ""
) -> dict:
    """Generate a coverage-first structured study package."""
    notes_text = _normalize_notes(notes_text)
    if not notes_text:
        raise ValueError("Notes text is empty.")

    groq_key = api_key if provider == "Groq" and api_key else os.environ.get("GROQ_API_KEY", "")
    anthropic_key = api_key if provider == "Anthropic" and api_key else os.environ.get("ANTHROPIC_API_KEY", "")
    openai_key = api_key if provider == "OpenAI" and api_key else os.environ.get("OPENAI_API_KEY", "")
    gemini_key = api_key if provider == "Google Gemini" and api_key else os.environ.get("GEMINI_API_KEY", "")

    if provider == "Demo Mode (Offline / No Key)":
        return _generate_fallback_demo(notes_text)

    if provider == "Groq" or (provider == "Auto-Detect" and groq_key):
        key = api_key if api_key else groq_key
        if key:
            return _generate_with_groq(notes_text, key, model)

    if provider == "Anthropic" or (provider == "Auto-Detect" and anthropic_key):
        key = api_key if api_key else anthropic_key
        if key:
            return _generate_with_anthropic(notes_text, key, model or "claude-3-5-haiku-20241022")

    if provider == "Google Gemini" or (provider == "Auto-Detect" and gemini_key):
        key = api_key if api_key else gemini_key
        if key:
            return _generate_with_gemini(notes_text, key, model or "gemini-1.5-flash")

    if provider == "OpenAI" or (provider == "Auto-Detect" and openai_key):
        key = api_key if api_key else openai_key
        if key:
            return _generate_with_openai(notes_text, key, model or "gpt-4o-mini")

    if provider not in ["Auto-Detect", "Demo Mode (Offline / No Key)"]:
        raise ValueError(
            f"No API key provided for {provider}. "
            "Please enter your key in the sidebar or switch to Demo Mode."
        )

    return _generate_fallback_demo(notes_text)
