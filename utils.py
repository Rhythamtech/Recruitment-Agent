from langchain_community.document_loaders import PDFMinerLoader
from langchain_google_genai import GoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv
import re
import json
from typing import Any
import os

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

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
        "score": <float between 0 and 10>,
        "justification": "<max 2 sentences>"
        }}

        REQUIREMENTS:
        - Output must be valid JSON only.
        - Do not include commentary outside the JSON block.
        - The justification must be objective and tied directly to the job requirements.
        """
)


resume_parse_prompt = PromptTemplate.from_template(
    """
You are a strict parser. Convert the following resume text into JSON matching the "Standard schema" shown below. Output ONLY valid JSON. Do not include explanations or markdown.

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
- For each experience, include at least 1 bullet in achievements; if none exist, copy a summarized sentence to achievements.
- If uncertain, set the field to null and include a "confidence" property with value 0.0-1.0 for that object.
    """ 
)

resume_url = "https://code.ics.uci.edu/wp-content/uploads/2020/06/Resume-Sample-1-Software-Engineer.pdf"

def llm_invoke(instruction: str) -> str:
    llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0, max_tokens=None, reasoning_format="parsed")
    response = llm.invoke( input = instruction)
    return response.content


# def llm_invoke(instruction: str) -> dict | None:
#     try:
#         llm = GoogleGenerativeAI(model="gemini-2.5-flash", api_key=api_key)
#         response = llm.invoke(input=instruction)
#         if hasattr(response, 'content'):
#             return extract_json_from_markdown(response.content)
#         return extract_json_from_markdown(str(response))
#     except Exception as e:
#         print(f"Error invoking LLM: {e}")
#         return None

def extract_candidate_info(resume_url):
    loader = PDFMinerLoader(resume_url)
    doc = loader.load()
    resume_text = doc[0].page_content
    response = llm_invoke(resume_parse_prompt.format(resume_text=resume_text))
    return response


def llm_score(resume_content: str, job_requirements: str) -> dict:    
    instruction = candidate_evaluation_prompt.format(
        job_requirements=job_requirements,
        resume_json= resume_content)

    response = llm_invoke(instruction)
    return response

def mock_zoom_meeting(candidate_email: str) -> dict:
    return {
        "candidate_email": candidate_email,
        "meeting_id": "1234567890",
        "meeting_url": "https://zoom.us/j/1234567890",
        "meeting_time": "2025-11-30T22:21:24+05:30"
    }


def send_email(candidate_email: str, subject: str, body: str) -> None:
    print(f"Sending email to {candidate_email} with subject: {subject}")    

def extract_json_from_markdown(md: str) -> Any:
    """
    Extract the first JSON code block from a Markdown string and parse it.
    Returns the parsed JSON object (e.g. dict or list).
    Raises ValueError if no JSON block found or parsing fails.
    """
    # Regex to match ```json ... ``` including multiline
    # Regex to match ```json ... ``` or just ``` ... ```
    pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
    match = re.search(pattern, md, re.MULTILINE)
    
    if match:
        json_text = match.group(1)
    else:
        # If no code block, assume the whole text might be JSON
        json_text = md.strip()

    try:
        return json.loads(json_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON content: {e}")
