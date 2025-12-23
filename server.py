from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from client.rq_client import queue
from contextlib import asynccontextmanager
from queues.graph import EmployeeRecruiterAgent, run_agent_workflow


class JobSpec(BaseModel):
    title: str
    description: str
    required_skills: list[str]

class CandidateInfo(BaseModel):
    name: str
    email: str
    phone: str
    resume_url: str

agent: EmployeeRecruiterAgent | None 

@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent
    agent = EmployeeRecruiterAgent()
    yield
    if agent is not None and hasattr(agent, "close"):
        agent.close()

app = FastAPI(title="Automated Recruitment Pipeline", lifespan=lifespan)

@app.post("/execute_workflow")
async def execute_workflow(candidate_info: CandidateInfo, thread_id: str, job_spec: JobSpec):
    return agent.invoke_agent(thread_id=thread_id, resume_url=candidate_info.resume_url, job_desc=job_spec.description)

@app.post("/rq/workflow")
async def rq_workflow(candidate_info: CandidateInfo, thread_id: str, job_spec: JobSpec):
    job = queue.enqueue(run_agent_workflow, thread_id=thread_id, resume_url=candidate_info.resume_url, job_desc=job_spec.description)

    return {"status": "ok", "job_id": job.id}

@app.get("/rq")
async def rq_get_status(job_id: str):
    job = queue.fetch_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"status": job.get_status(), "result" : job.return_value()}

@app.get("/health")
def health_check():
    return {"status": "ok"} 