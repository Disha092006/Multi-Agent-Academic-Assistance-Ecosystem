import os
import json
import re
from dotenv import load_dotenv
from crewai import Agent, Task
from langchain_openai import ChatOpenAI

load_dotenv()  # reads GROQ_API_KEY and OPENROUTER_API_KEY from .env

MAX_INPUT_CHARACTERS = 6000

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

MODEL_OPTIONS = {
    "llama": {
        "id": "llama-3.1-8b-instant",
        "label": "Llama 3.1 (fast, via Groq)",
        "base_url": GROQ_BASE_URL,
        "env_key": "GROQ_API_KEY",
    },
    "GPT-OSS 20B": {
        "id": "openai/gpt-oss-20b:free",
        "label": "GPT-OSS 20B (via OpenRouter)",
        "base_url": OPENROUTER_BASE_URL,
        "env_key": "OPENROUTER_API_KEY",
    },
}
DEFAULT_MODEL = "llama"


def get_llm(model_key):
    info = MODEL_OPTIONS.get(model_key, MODEL_OPTIONS[DEFAULT_MODEL])
    api_key = os.environ.get(info["env_key"])

    if not api_key:
        raise ValueError(
            f"{info['env_key']} is missing from your .env file. "
            f"Add a line like: {info['env_key']}=your_actual_key_here"
        )

    return ChatOpenAI(
        model=info["id"],
        base_url=info["base_url"],
        api_key=api_key,
        temperature=0.3,
        # Reasoning-style models (which the OpenRouter auto-router may
        # select) use tokens internally to "think" before writing a
        # final answer. A low limit can cut them off before they ever
        # produce visible output, especially for longer tasks like the
        # quiz. 2048 gives enough room for both thinking and the answer.
        max_tokens=4096,
    )


def generate_text(llm, prompt):
    response = llm.invoke(prompt)
    text = response.content.strip() if hasattr(response, "content") else str(response).strip()

    if not text:
        raise ValueError(
            "The model returned an empty response (this can happen with "
            "some free/reasoning models on complex tasks). Try a "
            "different model from the dropdown."
        )

    return text


def build_agents_and_tasks(document_text, llm, include_notes=True, include_quiz=True, include_revision=True):
    trimmed_text = document_text[:MAX_INPUT_CHARACTERS]

    if include_revision:
        include_notes = True
        include_quiz = True

    result = {
        "notes_agent": None, "notes_prompt": None,
        "quiz_agent": None, "quiz_prompt": None,
        "revision_agent": None, "revision_prompt_template": None,
    }

    if include_notes:
        result["notes_agent"] = Agent(
            role="Academic Notes Writer",
            goal="Turn study material into clear notes",
            backstory="You are a teacher who writes clear, organized study notes.",
            llm=llm,
            verbose=False,
            allow_delegation=False,
        )
        result["notes_prompt"] = (
            "Write structured notes based on the material below. "
            "Use '## ' for headings and '**bold**' for key terms. "
            "Use only information from the material. Respond with the "
            "notes directly - no introduction, no explanation of what "
            "you're doing.\n\nMATERIAL:\n" + trimmed_text
        )

    if include_quiz:
        result["quiz_agent"] = Agent(
            role="Quiz Creator",
            goal="Create multiple-choice quiz questions as JSON",
            backstory="You are a quiz designer who always replies in valid JSON.",
            llm=llm,
            verbose=False,
            allow_delegation=False,
        )
        result["quiz_prompt"] = (
            "Create 5 multiple-choice questions from the material below.\n\n"
            "Reply with ONLY a JSON array, nothing else. Each item needs "
            'these keys: "question" (string), "options" (array of 4 '
            'strings), "correct_index" (0-3), "topic" (2-5 word string).\n\n'
            "MATERIAL:\n" + trimmed_text
        )

    if include_revision:
        result["revision_agent"] = Agent(
            role="Revision Planner",
            goal="Build a 2-day study plan from the notes and quiz",
            backstory="You are a study coach who builds practical revision schedules.",
            llm=llm,
            verbose=False,
            allow_delegation=False,
        )
        result["revision_prompt_template"] = (
            "Using the notes and quiz below, write a 2-day revision "
            "plan. Use '## Day 1' and '## Day 2' headings. List 3-4 "
            "topics per day with a study activity for each. Respond "
            "with the plan directly - no introduction.\n\n"
            "NOTES:\n{notes}\n\nQUIZ:\n{quiz}"
        )

    return result


def run_pipeline(document_text, include_notes=True, include_quiz=True, include_revision=True, model_key=DEFAULT_MODEL):
    llm = get_llm(model_key)
    setup = build_agents_and_tasks(document_text, llm, include_notes, include_quiz, include_revision)

    notes_output = None
    quiz_output = None
    revision_output = None

    if setup["notes_prompt"]:
        notes_output = generate_text(llm, setup["notes_prompt"])

    if setup["quiz_prompt"]:
        quiz_output = generate_text(llm, setup["quiz_prompt"])

    if setup["revision_prompt_template"]:
        revision_prompt = setup["revision_prompt_template"].format(
            notes=notes_output or "(not generated)",
            quiz=quiz_output or "(not generated)",
        )
        revision_output = generate_text(llm, revision_prompt)

    return {
        "notes_output": notes_output,
        "quiz_output": quiz_output,
        "revision_output": revision_output,
    }


def parse_quiz_json(raw_output):
    text = raw_output.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    text_no_fences = re.sub(r"```(json)?", "", text).strip()
    try:
        return json.loads(text_no_fences)
    except json.JSONDecodeError:
        pass

    blocks = [b.strip() for b in re.split(r"\n\s*\n", text_no_fences) if b.strip()]
    if len(blocks) > 1:
        fixed_blocks = []
        for block in blocks:
            if block.startswith("[") and block.endswith("]"):
                inner = block[1:-1].strip()
                fixed_blocks.append("{" + inner + "}")
            else:
                fixed_blocks.append(block)
        combined = "[" + ",\n".join(fixed_blocks) + "]"
        try:
            return json.loads(combined)
        except json.JSONDecodeError:
            text_no_fences = combined

    match = re.search(r"\[.*\]", text_no_fences, re.DOTALL)
    candidate = match.group(0) if match else text_no_fences
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    try:
        from json_repair import repair_json
        repaired = repair_json(candidate)
        parsed = json.loads(repaired)
        if isinstance(parsed, list) and len(parsed) > 0:
            return parsed
    except Exception:
        pass

    return None


def answer_question(document_text, question, model_key=DEFAULT_MODEL, max_context_characters=6000):
    llm = get_llm(model_key)
    context = document_text[:max_context_characters]
    prompt = (
        "Answer the question using ONLY the information in the "
        "material below. If the answer isn't in the material, say "
        "'I couldn't find that in the document.' Be concise.\n\n"
        f"MATERIAL:\n{context}\n\n"
        f"QUESTION: {question}\n\nANSWER:"
    )
    return generate_text(llm, prompt)
