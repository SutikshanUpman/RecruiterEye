from backend.agent.llm import ask_llm


def get_keywords(job_input):
    """Turns a job description or a job role name into a list of skill keywords."""
    job_input = job_input[:3000]
    prompt = (
        "Extract the technical skill keywords a recruiter would look for "
        "from this job description or job role.\n"
        "Rules: return 10 to 15 keywords, lowercase, comma-separated, "
        "no explanation, no numbering.\n\n"
        f"Job input: {job_input}"
    )
    reply = ask_llm(prompt)
    keywords = [k.strip().lower() for k in reply.replace("\n", ",").split(",")]
    return [k for k in keywords if k]


if __name__ == "__main__":
    jd = """
    We are looking for an AI Engineer Intern to join our applied ML team.
    You will build and deploy LLM-powered features using Python and FastAPI.
    Experience with RAG pipelines, vector databases such as ChromaDB or Pinecone,
    and prompt engineering is a plus. You should be comfortable with Git, Docker,
    and REST APIs. Familiarity with PyTorch or TensorFlow and basic SQL is expected.
    Strong communication skills and the ability to work in a fast-paced team.
    """
    print(get_keywords(jd))