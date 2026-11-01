from groq import Groq
from backend.core.config import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)

CHEAP_MODEL = "openai/gpt-oss-20b"
HEAVY_MODEL = "openai/gpt-oss-120b"


def ask_llm(prompt, model=CHEAP_MODEL, temperature=0):
    """Sends a prompt to Groq and returns the reply as plain text."""
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    print("cheap:", ask_llm("Say hello in one short sentence."))
    print("heavy:", ask_llm("Say hello in one short sentence.", HEAVY_MODEL))