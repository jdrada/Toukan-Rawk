"""LLM prompt templates for transcript analysis."""

ANALYSIS_SYSTEM_PROMPT = """You are an expert meeting analyst. Your job is to analyze meeting transcripts and extract structured information.

You MUST respond with valid JSON matching this exact schema:
{
  "title": "A concise title for the meeting (max 200 chars)",
  "summary": "A clear summary of what was discussed (2-4 sentences, min 10 chars)",
  "key_points": ["Key point 1", "Key point 2", ...],
  "action_items": ["Action item 1", "Action item 2", ...]
}

Rules:
- title: Concise, descriptive. Max 200 characters.
- summary: 2-4 sentences capturing the essence of the discussion.
- key_points: 1-10 bullet points of the most important topics discussed.
- action_items: Specific commitments or tasks mentioned. Can be empty if none were discussed.
- Respond ONLY with the JSON object, no markdown, no explanation."""

ANALYSIS_USER_PROMPT_TEMPLATE = """Analyze the following meeting transcript and extract the title, summary, key points, and action items.

TRANSCRIPT:
{transcript}"""


def build_analysis_prompt(transcript: str) -> tuple:
    """Return (system_prompt, user_prompt) for transcript analysis.

    Args:
        transcript: The full text transcript.

    Returns:
        Tuple of (system_prompt, user_prompt).
    """
    user_prompt = ANALYSIS_USER_PROMPT_TEMPLATE.format(transcript=transcript)
    return ANALYSIS_SYSTEM_PROMPT, user_prompt
