DRAFT_PROMPT = """
Write a short follow-up message from {my_name} to {their_name} after meeting at a professional event.

WHO THEY ARE:
- {role} at {company}
- Key thing about them: {top_talking_point}

WHAT WE TALKED ABOUT:
{met_notes}

SEND CHANNEL: {channel}  (linkedin_dm | email | twitter_dm)

Rules:
- 3-5 sentences. No longer.
- Reference something SPECIFIC from the conversation notes.
- End with one natural, low-pressure hook — a question, resource offer, or shared next step.
- Adjust tone for channel: email slightly more formal, DMs shorter and more casual.
- Do NOT open with "It was great meeting you at [event name]".
- Do NOT use: synergy, leverage, circle back, touch base, reach out, connect.
- Tone: warm and direct. Like a message you'd actually want to receive.

Return ONLY the message text. Nothing else.
"""
