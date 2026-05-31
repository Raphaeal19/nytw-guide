import ollama
from server.config import settings
from server.drafter.prompts import DRAFT_PROMPT


def draft_message(attendance, channel: str, extra_context: str | None = None) -> str:
    person = attendance.person
    top_point = ""
    if person.talking_points:
        points = sorted(person.talking_points, key=lambda x: x.get("priority", 99))
        if points:
            top_point = points[0].get("text", "")

    notes = attendance.met_notes or ""
    if extra_context:
        notes = f"{notes}\n\nAdditional context: {extra_context}".strip()

    prompt = DRAFT_PROMPT.format(
        my_name=settings.my_name,
        their_name=person.name,
        role=person.role or "professional",
        company=person.company or "their company",
        top_talking_point=top_point,
        met_notes=notes or "(no notes provided)",
        channel=channel,
    )

    response = ollama.chat(
        model=settings.ollama_model,
        messages=[{"role": "user", "content": prompt}],
        options={"base_url": settings.ollama_base_url},
    )
    return response["message"]["content"].strip()
