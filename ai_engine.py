"""
ai_engine.py
Wraps calls to LLM APIs (Groq, Anthropic, OpenAI / OpenRouter, Google Gemini)
and includes a Smart Local NLP Study Engine fallback so PDF uploads and custom
notes produce real concept flashcards, structured summaries, and topic-grounded
multiple-choice quizzes even when no API key is configured.

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
import hashlib
import urllib.request
import urllib.error
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

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

# Curated presets for the built-in OS & Biology demo buttons
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
            {"front": "What is a Race Condition?", "back": "A flaw where the output depends on the non-deterministic timing or sequence of concurrent threads."},
            {"front": "What is Mutual Exclusion?", "back": "The guarantee that only one process can execute inside its critical section at any given instant."},
            {"front": "How do Semaphore wait() and signal() operations work?", "back": "wait() (P) decrements the semaphore and blocks if <= 0; signal() (V) increments it and wakes a waiting process."},
            {"front": "What are the four Coffman Conditions for Deadlock?", "back": "Mutual Exclusion, Hold and Wait, No Preemption, and Circular Wait."},
            {"front": "What is the purpose of Banker's Algorithm?", "back": "A deadlock avoidance algorithm that simulates resource allocation to verify the system remains in a safe state."}
        ],
        "quiz": [
            {
                "question": "Which condition is NOT one of the Coffman conditions required for a deadlock?",
                "options": ["Mutual Exclusion", "Circular Wait", "Preemptive Scheduling", "Hold and Wait"],
                "correct_index": 2,
                "explanation": "No Preemption (not Preemptive Scheduling) is required for deadlock; resources cannot be forcibly seized."
            },
            {
                "question": "What happens when a process invokes wait() (or P()) on a semaphore when the resource is unavailable?",
                "options": ["The semaphore increments to 1", "The process blocks until another process calls signal()", "An exception is raised", "The process terminates immediately"],
                "correct_index": 1,
                "explanation": "wait() blocks the calling process until another process releases the resource via signal() (V)."
            },
            {
                "question": "Which criterion guarantees that a waiting process will eventually enter its critical section without starving?",
                "options": ["Mutual Exclusion", "Bounded Waiting", "Resource Isolation", "Strict Alternation"],
                "correct_index": 1,
                "explanation": "Bounded Waiting places a limit on how many times other processes can enter before a waiting process is granted access."
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
            "Light reactions split water in the thylakoid membrane, generating ATP and NADPH while releasing O2.",
            "The Calvin cycle fixes atmospheric CO2 into sugars in the chloroplast stroma using ATP and NADPH.",
            "Glycolysis yields a net of 2 ATP, 2 NADH, and 2 Pyruvate per glucose molecule in the cytosol.",
            "Oxidative phosphorylation generates 28-32 ATP via ATP synthase with oxygen as the terminal electron acceptor."
        ],
        "flashcards": [
            {"front": "What is the role of ATP Synthase?", "back": "An enzyme that harnesses the proton gradient across the inner mitochondrial membrane to synthesize 28-32 ATP."},
            {"front": "Where do the Light-Dependent Reactions occur?", "back": "In the thylakoid membranes of chloroplasts, producing ATP and NADPH."},
            {"front": "What occurs during Glycolysis?", "back": "Anaerobic breakdown of glucose in the cytosol producing a net gain of 2 ATP."},
            {"front": "What is the terminal electron acceptor in aerobic respiration?", "back": "Oxygen (O2), which accepts electrons at the end of the Electron Transport Chain."}
        ],
        "quiz": [
            {
                "question": "Where does the Calvin Cycle occur inside a plant cell?",
                "options": ["Thylakoid lumen", "Stroma of the chloroplast", "Mitochondrial matrix", "Cytosol"],
                "correct_index": 1,
                "explanation": "The Calvin cycle fixes CO2 into sugars inside the stroma of the chloroplast."
            },
            {
                "question": "What is the net yield of ATP produced directly during Glycolysis per glucose molecule?",
                "options": ["4 ATP", "2 ATP", "28-32 ATP", "6 ATP"],
                "correct_index": 1,
                "explanation": "Glycolysis takes place in the cytosol and yields 2 net ATP per glucose molecule."
            },
            {
                "question": "What is the terminal electron acceptor in the aerobic Electron Transport Chain?",
                "options": ["NADPH", "Oxygen (O2)", "Carbon dioxide (CO2)", "Pyruvate"],
                "correct_index": 1,
                "explanation": "Oxygen serves as the terminal electron acceptor in oxidative phosphorylation."
            }
        ]
    }
}

STOPWORDS = {
    "the", "and", "for", "that", "this", "with", "from", "are", "was", "were",
    "have", "has", "had", "not", "but", "what", "all", "when", "where", "which",
    "who", "will", "would", "could", "should", "can", "may", "might", "must",
    "into", "onto", "upon", "over", "under", "between", "among", "through",
    "during", "before", "after", "above", "below", "about", "against", "within",
    "without", "because", "while", "where", "after", "so", "though", "since",
    "until", "whether", "before", "although", "nor", "like", "once", "unless",
    "now", "except", "also", "very", "often", "however", "too", "usually",
    "really", "early", "never", "always", "sometimes", "together", "likely",
    "simply", "generally", "instead", "actually", "again", "rather", "almost",
    "especially", "either", "neither", "both", "each", "every", "other", "some",
    "such", "no", "nor", "only", "own", "same", "than", "then", "their", "there",
    "these", "they", "those", "them", "its", "our", "your", "his", "her", "been",
    "being", "does", "did", "doing", "done", "make", "made", "makes", "used",
    "using", "uses", "use", "page", "notes", "lecture", "chapter", "section",
    "example", "examples", "called", "known", "defined", "refers", "means"
}


def _normalize_notes(notes_text: str) -> str:
    """Lightly clean extraction/OCR noise without changing the source meaning."""
    text = notes_text.replace("\x00", " ")
    text = text.replace("\ufffd", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove "--- Page X ---" markers added by PDF extractor so they don't become flashcards
    text = re.sub(r"^---\s*Page\s*\d+\s*---\s*$", "", text, flags=re.MULTILINE | re.IGNORECASE)

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

    points = []
    seen_points = set()
    for p in data["key_points"]:
        p = str(p).strip()
        key = re.sub(r"\W+", " ", p.lower()).strip()
        if p and key and key not in seen_points:
            seen_points.add(key)
            points.append(p)
    data["key_points"] = points

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
        "llama-3.3-70b-versatile",
        "openai/gpt-oss-20b",
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
    model: str = ""
) -> dict:
    from openai import OpenAI

    # Automatically support both OpenRouter keys (sk-or-...) and standard OpenAI keys (sk-...)
    is_openrouter = api_key.startswith("sk-or-") or bool(os.environ.get("OPENROUTER_API_KEY"))
    if is_openrouter:
        client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
        chosen_model = model or "openrouter/free"
    else:
        client = OpenAI(api_key=api_key)
        chosen_model = model or "gpt-4o-mini"

    response = client.chat.completions.create(
        model=chosen_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(notes_text)}
        ],
        temperature=0.15,
        response_format={"type": "json_object"},
        max_tokens=6000,
    )

    return _clean_json_response(response.choices[0].message.content)


def _generate_with_gemini(notes_text: str, api_key: str,
                          model: str = "") -> dict:
    import google.generativeai as genai
    genai.configure(api_key=api_key)

    candidates = [model] if model else ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
    last_err = None
    for cand in candidates:
        if not cand:
            continue
        try:
            gemini_model = genai.GenerativeModel(
                model_name=cand,
                system_instruction=SYSTEM_PROMPT,
                generation_config={
                    "response_mime_type": "application/json",
                    "temperature": 0.15,
                    "max_output_tokens": 6000,
                }
            )
            response = gemini_model.generate_content(_build_user_prompt(notes_text))
            return _clean_json_response(response.text)
        except Exception as e:
            last_err = e
            continue
    raise ValueError(f"Gemini generation failed: {last_err}")


def _try_free_cloud_llm(notes_text: str) -> dict | None:
    """
    Attempt a zero-key cloud LLM generation with a fast timeout.
    If rate-limited or unavailable on shared cloud IPs, returns None so
    the Smart Local NLP Study Engine takes over immediately.
    """
    try:
        payload = json.dumps({
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_prompt(notes_text[:12000])}
            ],
            "model": "openai",
            "jsonMode": True
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://text.pollinations.ai/",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=9) as resp:
            raw = resp.read().decode("utf-8")
            parsed = _clean_json_response(raw)
            if parsed.get("flashcards") and parsed.get("quiz"):
                return parsed
    except Exception:
        return None
    return None


# ==============================================================================
# SMART LOCAL NLP STUDY ENGINE (Works 100% Offline / Without Any API Key)
# ==============================================================================

def _extract_sentences_and_headings(notes_text: str) -> tuple[list[str], list[str]]:
    """Split normalized notes into clean headings and informative sentences."""
    headings = []
    raw_blocks = []

    for line in notes_text.splitlines():
        clean = line.strip(" \t-*•#")
        if not clean:
            continue
        # Check if line looks like a section heading
        if (line.strip().startswith("#") or
                (len(clean.split()) <= 8 and not clean.endswith((".", "?", "!")) and clean[0].isupper())):
            if len(clean) >= 3 and not re.match(r"^(page|slide|chapter|unit)\s*\d+$", clean, re.I):
                headings.append(clean.rstrip(":"))
            continue
        raw_blocks.append(clean)

    joined = "\n".join(raw_blocks)
    candidates = re.split(r"(?<=[.!?])\s+|\n+", joined)

    sentences = []
    seen = set()
    for s in candidates:
        s = re.sub(r"^\s*(?:[\d]+[.)]|\([a-zA-Z0-9]+\)|[-*•])\s*", "", s).strip()
        if len(s) < 22 or len(s.split()) < 4:
            continue
        if not s.endswith((".", "!", "?")):
            s = s + "."
        norm = re.sub(r"\W+", " ", s.lower()).strip()
        if norm and norm not in seen:
            seen.add(norm)
            sentences.append(s)

    return headings, sentences


def _extract_concept_pairs(sentences: list[str]) -> list[dict]:
    """
    Extract structured (term, definition/detail, full_sentence, kind) records
    from natural sentences using syntactic patterns.
    """
    concepts = []
    seen_terms = set()

    patterns = [
        # Pattern 1: "Term: definition" or "Term - definition"
        (r"^([A-Z][A-Za-z0-9_/\-\s()]{1,48}?)\s*(?::|—|–|-)\s+(.{15,})$", "definition"),
        # Pattern 2: "X is/are defined as / refers to / means / represents Y"
        (r"^(?:A|An|The)?\s*([A-Za-z][A-Za-z0-9_/\-\s()]{1,48}?)\s+(?:is defined as|are defined as|refers to|means|is known as|represents|denotes)\s+(.{15,})$", "definition"),
        # Pattern 3: "X is/are a/an/the Y"
        (r"^(?:A|An|The)?\s*([A-Za-z][A-Za-z0-9_/\-\s()]{1,42}?)\s+(?:is|are)\s+((?:a|an|the|one of|used to|designed to|responsible for|ordered|mutable|immutable)\s+.{12,})$", "definition"),
        # Pattern 4: "X occurs/happens/arises when Y"
        (r"^(?:A|An|The)?\s*([A-Za-z][A-Za-z0-9_/\-\s()]{1,42}?)\s+(?:occurs|happens|arises|takes place)\s+(when\s+.{12,}|in\s+.{12,}|during\s+.{12,})$", "condition"),
        # Pattern 5: "X provides/converts/generates/operates/translates/etc. Y"
        (r"^(?:A|An|The)?\s*([A-Za-z][A-Za-z0-9_/\-\s()]{1,45}?)\s+((?:provides|converts|generates|produces|breaks down|consists of|requires|uses|stores|manages|controls|prevents|avoids|fixes|allows|operates|translates|forwards|executes|performs|handles|processes|maps|enables|supports|contains|includes)\s+.{12,})$", "mechanism"),
    ]

    for s in sentences:
        matched = False
        for pat, kind in patterns:
            m = re.match(pat, s)
            if m:
                term = m.group(1).strip(" .,:;-—\"'")
                if term.startswith("(") and term.endswith(")"):
                    term = term[1:-1].strip()
                detail = m.group(2).strip()
                # Filter out pronouns or overly generic subject starts
                if term.lower() in STOPWORDS or term.lower().split()[0] in {
                    "it", "they", "this", "that", "these", "those", "there", "here", "when", "if", "while", "each", "both", "together"
                }:
                    continue
                if len(term.split()) > 6 or len(term) < 2:
                    continue
                term_key = term.lower()
                if term_key not in seen_terms:
                    seen_terms.add(term_key)
                    concepts.append({
                        "term": term,
                        "detail": detail.rstrip(".") + ".",
                        "sentence": s,
                        "kind": kind
                    })
                    matched = True
                    break

        if not matched:
            # Extract most salient technical term or capitalized/multi-word noun phrase in the sentence
            words = re.findall(r"\b[A-Za-z][A-Za-z0-9_\-+]{2,}\b", s)
            candidates = [
                w for w in words
                if w.lower() not in STOPWORDS and len(w) >= 4
            ]
            # Prefer capitalized internal terms or longer technical terms
            candidates.sort(key=lambda w: (w[0].isupper(), len(w)), reverse=True)
            chosen_term = None
            for cand in candidates:
                if cand.lower() not in seen_terms:
                    chosen_term = cand
                    break
            if chosen_term:
                seen_terms.add(chosen_term.lower())
                concepts.append({
                    "term": chosen_term,
                    "detail": s,
                    "sentence": s,
                    "kind": "concept"
                })

    return concepts


def _highlight_term_in_sentence(sentence: str, term: str) -> str:
    """Bold the first occurrence of `term` inside `sentence` for readable Markdown."""
    if not term or "**" in sentence:
        return sentence
    pattern = re.compile(re.escape(term), re.IGNORECASE)
    return pattern.sub(lambda m: f"**{m.group(0)}**", sentence, count=1)


def _generate_fallback_demo(notes_text: str) -> dict:
    """
    Smart Local NLP Study Engine that turns ANY uploaded PDF/notes into a
    structured summary, key points, active-recall flashcards, and a realistic
    multiple-choice quiz without needing an API key.
    """
    lower = notes_text.lower()

    # Use rich presets only when the exact built-in sample notes are clicked
    if "6co2 + 6h2o + light" in lower and "thylakoid membranes" in lower and len(notes_text) < 900:
        return DEMO_PRESETS["Cellular Biology"]

    if "coffman conditions" in lower and "banker's algorithm" in lower and len(notes_text) < 900:
        return DEMO_PRESETS["Operating Systems"]

    normalized = _normalize_notes(notes_text)
    headings, sentences = _extract_sentences_and_headings(normalized)

    if not sentences:
        # Handle very short bullet or fragment notes
        sentences = [
            line.strip(" -*•\t")
            for line in normalized.splitlines()
            if len(line.strip()) >= 10
        ]

    if not sentences:
        sentences = ["The uploaded notes did not contain enough readable text to build a study package."]

    concepts = _extract_concept_pairs(sentences)

    # 1. Build a clean, descriptive Title
    if headings:
        title = headings[0]
    elif concepts:
        top_terms = [c["term"] for c in concepts[:3]]
        title = " & ".join(top_terms[:2]) if len(top_terms) >= 2 else top_terms[0]
    else:
        title = " ".join(sentences[0].split()[:6]).strip(" .,:;")
    if len(title) > 68:
        title = title[:65].rsplit(" ", 1)[0] + "..."

    # 2. Build a Multi-Section Structured Summary
    defs = [c for c in concepts if c["kind"] == "definition"]
    mechs = [c for c in concepts if c["kind"] in ("mechanism", "condition")]
    others = [c for c in concepts if c["kind"] == "concept"]

    summary_parts = []
    overview_sents = sentences[:min(3, len(sentences))]
    highlighted_overview = " ".join(
        _highlight_term_in_sentence(
            s,
             next((c["term"] for c in concepts if c["sentence"] == s), "")
        )
        for s in overview_sents
    )
    summary_parts.append(f"### 📌 Core Overview\n\n{highlighted_overview}")

    if defs:
        def_bullets = "\n".join(
            f"- **{c['term']}**: {c['detail']}"
            for c in defs[:6]
        )
        summary_parts.append(f"### 🔑 Key Definitions & Concepts\n\n{def_bullets}")

    if mechs:
        mech_bullets = "\n".join(
            f"- {_highlight_term_in_sentence(c['sentence'], c['term'])}"
            for c in mechs[:6]
        )
        summary_parts.append(f"### ⚙️ Mechanisms, Processes & Rules\n\n{mech_bullets}")

    remaining_sents = [
        s for s in sentences[3:]
        if s not in {c["sentence"] for c in defs[:6] + mechs[:6]}
    ]
    if remaining_sents:
        extra_bullets = "\n".join(
            f"- {_highlight_term_in_sentence(s, next((c['term'] for c in others if c['sentence'] == s), ''))}"
            for s in remaining_sents[:6]
        )
        summary_parts.append(f"### 📚 Additional Revision Notes\n\n{extra_bullets}")

    summary = "\n\n".join(summary_parts)

    # 3. Build High-Yield Key Points (6 to 10 distinct points)
    key_points = sentences[:min(10, len(sentences))]

    # 4. Build Active-Recall Flashcards (Real Questions, Never "Concept 1")
    flashcards = []
    for c in concepts[:10]:
        term = c["term"]
        kind = c["kind"]
        if kind == "definition":
            front = f"What is {term}?"
            back = c["detail"].capitalize() if c["detail"] and c["detail"][0].islower() else c["detail"]
        elif kind == "condition":
            front = f"When or how does {term} occur?"
            back = c["sentence"]
        elif kind == "mechanism":
            front = f"What is the role or mechanism of {term}?"
            back = c["sentence"]
        else:
            front = f"Key Concept: How do the notes describe {term}?"
            back = c["sentence"]
        flashcards.append({"front": front, "back": back})

    if not flashcards:
        for i, s in enumerate(sentences[:6]):
            words = [w.strip(".,:;()") for w in s.split() if len(w) > 4 and w.lower() not in STOPWORDS]
            focus = words[0] if words else f"Topic {i + 1}"
            flashcards.append({
                "front": f"Explain the note's key takeaway regarding {focus}:",
                "back": s
            })

    # 5. Build Realistic Self-Graded Multiple-Choice Quiz
    quiz = []
    all_terms = [c["term"] for c in concepts if len(c["term"]) >= 3]
    # Add backup technical terms from the text if there are fewer than 4 concept terms
    if len(all_terms) < 4:
        extra_words = []
        for s in sentences:
            for w in re.findall(r"\b[A-Za-z][A-Za-z0-9_\-]{3,}\b", s):
                if w.lower() not in STOPWORDS and w not in all_terms and w not in extra_words:
                    extra_words.append(w)
        all_terms.extend(extra_words[:8])

    fallback_terms = ["System Process", "Data Structure", "Control Mechanism", "Primary Component"]
    for ft in fallback_terms:
        if len(all_terms) < 4 and ft not in all_terms:
            all_terms.append(ft)

    for idx, c in enumerate(concepts[:8]):
        term = c["term"]
        sent = c["sentence"]
        kind = c["kind"]

        # Pick 3 distinct distractor terms from the document
        distractor_terms = [
            t for t in all_terms
            if t.lower() != term.lower() and t.lower() not in term.lower() and term.lower() not in t.lower()
        ][:3]
        while len(distractor_terms) < 3:
            filler = f"Alternative Concept {len(distractor_terms) + 1}"
            if filler not in distractor_terms:
                distractor_terms.append(filler)

        # Deterministic rotation of correct_index (0, 1, 2, 3) based on question hash
        q_hash = int(hashlib.md5(sent.encode("utf-8")).hexdigest()[:6], 16)
        correct_idx = (idx + q_hash) % 4

        if kind == "definition":
            question = f"Which concept or term from the notes is described as: \"{c['detail'].rstrip('.')}\"?"
            correct_answer = term
            distractors = distractor_terms[:3]
        else:
            # Cloze (fill-in-the-blank) question using the actual term in the sentence
            blanked = re.sub(re.escape(term), "________", sent, count=1, flags=re.IGNORECASE)
            if "________" in blanked:
                question = f"Complete the following statement from your notes: \"{blanked}\""
                correct_answer = term
                distractors = distractor_terms[:3]
            else:
                question = f"Which concept in the notes is directly associated with: \"{sent}\"?"
                correct_answer = term
                distractors = distractor_terms[:3]

        options = list(distractors)
        options.insert(correct_idx, correct_answer)

        quiz.append({
            "question": question,
            "options": options[:4],
            "correct_index": correct_idx,
            "explanation": f"Directly from the notes: {sent}"
        })

    return _validate_package({
        "title": title,
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
    """
    Generate a coverage-first structured study package.
    Automatically uses any configured LLM API key (Groq, Gemini, OpenRouter, OpenAI, Anthropic),
    tries a zero-key cloud LLM if no key is present, and seamlessly falls back to the
    Smart Local NLP Study Engine so the user NEVER sees an API key error or dummy output.
    """
    notes_text = _normalize_notes(notes_text)
    if not notes_text:
        raise ValueError("Notes text is empty.")

    api_key = (api_key or "").strip()

    groq_key = (api_key if provider == "Groq" and api_key else "") or os.environ.get("GROQ_API_KEY", "")
    gemini_key = (api_key if provider == "Google Gemini" and api_key else "") or os.environ.get("GEMINI_API_KEY", "")
    anthropic_key = (api_key if provider == "Anthropic" and api_key else "") or os.environ.get("ANTHROPIC_API_KEY", "")
    openai_key = (
        (api_key if provider == "OpenAI" and api_key else "")
        or os.environ.get("OPENAI_API_KEY", "")
        or os.environ.get("OPENROUTER_API_KEY", "")
    )

    # Also auto-detect a pasted key even if provider dropdown was left on Auto-Detect
    if api_key and provider == "Auto-Detect":
        if api_key.startswith("gsk_"):
            groq_key = api_key
        elif api_key.startswith("AIza"):
            gemini_key = api_key
        elif api_key.startswith("sk-ant-"):
            anthropic_key = api_key
        elif api_key.startswith("sk-"):
            openai_key = api_key

    if provider == "Demo Mode (Offline / No Key)":
        return _generate_fallback_demo(notes_text)

    try:
        if provider == "Groq" or (provider == "Auto-Detect" and groq_key):
            if groq_key:
                return _generate_with_groq(notes_text, groq_key, model)

        if provider == "Google Gemini" or (provider == "Auto-Detect" and gemini_key):
            if gemini_key:
                return _generate_with_gemini(notes_text, gemini_key, model)

        if provider == "Anthropic" or (provider == "Auto-Detect" and anthropic_key):
            if anthropic_key:
                return _generate_with_anthropic(notes_text, anthropic_key, model or "claude-3-5-haiku-20241022")

        if provider == "OpenAI" or (provider == "Auto-Detect" and openai_key):
            if openai_key:
                return _generate_with_openai(notes_text, openai_key, model)
    except Exception:
        # If an API call fails due to quota/network, gracefully fall back rather than crashing
        pass

    # If no API key is configured, attempt zero-key cloud LLM first, then Smart Local NLP Engine
    cloud_pack = _try_free_cloud_llm(notes_text)
    if cloud_pack:
        return cloud_pack

    return _generate_fallback_demo(notes_text)
