import os
import re
import json
import logging
import requests
import tempfile
from typing import Any, Optional, Dict
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

# --- Prompts ---

candidate_evaluation_prompt = PromptTemplate.from_template(
    """
    You are an experienced hiring manager. Evaluate the candidate strictly against the provided job requirements.

    JOB REQUIREMENTS (text):
    {job_requirements}

    CANDIDATE RESUME (structured JSON):
    {resume_json}

    TASK:
    1. Analyze how well the candidate meets the job requirements.
    2. Provide a single numeric score from 0.0 to 10.0 (higher = better fit).
    3. Provide a concise justification (maximum 2 sentences) summarizing the key strengths and gaps relevant to the role.
    4. Base your evaluation ONLY on the information explicitly present in the resume.

    OUTPUT FORMAT (must be valid JSON, no extra text, no explanations):

    {{
    "score": float (0-10),
    "justification": "<max 2 sentences>"
    }}
    """
)

resume_parse_prompt = PromptTemplate.from_template(
    """
    You are a strict parser. Convert the following resume text into JSON matching the "Standard schema" shown below. Output ONLY valid JSON. 

    Standard schema:
    {{
      "id": "uuid",
      "name": "string",
      "label": "string (job title/role)",
      "contact": {{
        "email": "string",
        "phone": "string",
        "city": "string",
        "region": "string",
        "country": "string",
        "links": [
          {{"label":"GitHub","url":"string"}},
          {{"label":"LinkedIn","url":"string"}}
        ]
      }},
      "summary": "string",
      "experience": [
        {{
          "id":"uuid",
          "title":"string",
          "company":"string",
          "location":"string",
          "start_date":"YYYY-MM",
          "end_date":"YYYY-MM or PRESENT",
          "employment_type":"Full-time/Part-time/Contract/Internship",
          "achievements":["string"],
          "metrics":[{{"metric":"revenue/efficiency/etc","value":"string"}}],
          "keywords":["string"]
        }}
      ],
      "education":[
        {{
          "id":"uuid",
          "degree":"string",
          "field":"string",
          "school":"string",
          "start_date":"YYYY-MM",
          "end_date":"YYYY-MM",
          "gpa":"string",
          "honors":"string"
        }}
      ],
      "projects":[
        {{
          "id":"uuid",
          "title":"string",
          "description":"string",
          "technologies":["string"],
          "link":"string",
          "start_date":"YYYY-MM",
          "end_date":"YYYY-MM"
        }}
      ],
      "skills":[
        {{"name":"string","level":"beginner|intermediate|advanced|expert","years":number}}
      ],
      "certifications":[
        {{"name":"string","issuer":"string","date":"YYYY-MM"}}
      ],
      "languages":[
        {{"language":"string","proficiency":"basic|conversational|fluent|native"}}
      ],
      "volunteer":[
        {{"role":"string","organization":"string","start_date":"YYYY-MM","end_date":"YYYY-MM","description":"string"}}
      ],
      "updated_at":"YYYY-MM-DD"
    }}

    Resume text:
    ---
    {resume_text}
    ---
    Rules:
    - Normalize dates to YYYY-MM or "PRESENT".
    - Extract contact emails, phones, links into contact.links.
    - For each experience, include at least 1 bullet in achievements.
    """ 
)

# --- Core Functions ---

def llm_invoke(instruction: str) -> str:
    """Invokes the LLM (Groq) with the given instruction."""
    try:
        from langchain_groq import ChatGroq
        # Using a standard Groq model for reliability
        model_name = os.getenv("GROQ_MODEL", "llama3-70b-8192")
        llm = ChatGroq(model=model_name, temperature=0)
        response = llm.invoke(input=instruction)
        return response.content
    except Exception as e:
        logger.error(f"Error invoking Groq LLM: {e}")
        # Fallback or re-raise
        raise

def extract_json_from_markdown(md: str) -> Any:
    """Extracts JSON content from a markdown code block or raw string."""
    pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
    match = re.search(pattern, md, re.MULTILINE)
    json_text = match.group(1) if match else md.strip()
    
    try:
        return json.loads(json_text)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON: {json_text[:100]}...")
        raise ValueError(f"Invalid JSON content: {e}")

def extract_candidate_info(resume_url_or_path: str) -> Dict:
    """Downloads (if URL) and parses a PDF resume into structured JSON."""
    from langchain_community.document_loaders import PDFMinerLoader
    
    is_url = resume_url_or_path.startswith("http")
    
    if is_url:
        logger.info(f"Downloading resume from URL: {resume_url_or_path}")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            response = requests.get(resume_url_or_path)
            response.raise_for_status()
            tmp.write(response.content)
            tmp_path = tmp.name
    else:
        tmp_path = resume_url_or_path

    try:
        logger.info(f"Parsing PDF: {tmp_path}")
        loader = PDFMinerLoader(tmp_path)
        doc = loader.load()
        if not doc:
            raise ValueError("PDF loaded but no content found.")
        resume_text = doc[0].page_content
        
        response_content = llm_invoke(resume_parse_prompt.format(resume_text=resume_text))
        return extract_json_from_markdown(response_content)
    finally:
        if is_url and os.path.exists(tmp_path):
            os.remove(tmp_path)

def llm_score(resume_content: Any, job_requirements: str) -> Dict:
    """Scores a candidate's resume against job requirements using LLM."""
    if isinstance(resume_content, dict):
        resume_content = json.dumps(resume_content)
    
    instruction = candidate_evaluation_prompt.format(
        job_requirements=job_requirements,
        resume_json=resume_content
    )

    response_content = llm_invoke(instruction)
    return extract_json_from_markdown(response_content)

def mock_zoom_meeting(candidate_email: str) -> Dict:
    """Generates a mock Zoom meeting payload."""
    return {
        "candidate_email": candidate_email,
        "meeting_id": "123-456-7890",
        "meeting_url": "https://zoom.us/j/1234567890",
        "meeting_time": "2025-11-30T22:21:24+05:30"
    }

def send_email(candidate_email: str, subject: str, body: str) -> None:
    """Sends an email using the internal mail module."""
    import mail
    try:
        logger.info(f"Attempting to send email to {candidate_email}...")
        mail.send(subject=subject, receiver_mail=candidate_email, html_content=body)
        logger.info(f"✅ Email sent successfully to {candidate_email}")
    except Exception as e:
        logger.error(f"❌ Failed to send email to {candidate_email}: {e}")
        raise
