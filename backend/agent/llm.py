from groq import Groq
from backend.core.errors import ReviewError

client = None

CHEAP_MODEL = "openai/gpt-oss-20b"
HEAVY_MODEL = "openai/gpt-oss-120b"


def ask_llm(prompt: str, model: str = CHEAP_MODEL, temperature: float = 0) -> str:
    """Sends a prompt to Groq and returns the reply as plain text."""
    global client
    if client is None:
        from backend.core.config import GROQ_API_KEY

        if not GROQ_API_KEY:
            raise ReviewError("Groq is not configured on the server.", 503)
        client = Groq(api_key=GROQ_API_KEY, timeout=60, max_retries=0)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
    )
    content = response.choices[0].message.content if response.choices else None
    if not isinstance(content, str) or not content.strip():
        raise ReviewError("The model returned an empty response. Please try again.")
    return content.strip()


if __name__ == "__main__":
    print("cheap:", ask_llm("Say hello in one short sentence."))
    print("heavy:", ask_llm("Say hello in one short sentence.", HEAVY_MODEL))
