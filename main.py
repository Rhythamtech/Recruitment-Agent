import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from graph import EmployeeRecruiterAgent

app = FastAPI(title="Automated Recruitment Pipeline")

class JobSpec(BaseModel):
    title: str
    description: str
    required_skills: list[str]

class CandidateInfo(BaseModel):
    name: str
    email: str
    phone: str
    resume_url: str


# app-level agent instance (created on startup)
agent: Optional[EmployeeRecruiterAgent] = None


@app.on_event("startup")
def startup_event():
    """
    Create/reuse the agent at startup so you don't rebuild per-request.
    If EmployeeRecruiterAgent requires arguments (e.g., checkpointer), pass them here.
    """
    global agent
    agent = EmployeeRecruiterAgent()


@app.on_event("shutdown")
def shutdown_event():
    """
    Cleanup resources if your agent exposes any shutdown/close API.
    Add agent.close()/checkpointer.close() calls here if needed.
    """
    global agent
    try:
        if agent is not None and hasattr(agent, "close"):
            agent.close()
    except Exception:
        pass


@app.post("/execute_workflow")
def execute_workflow(candidate_info: CandidateInfo, thread_id: str, job_spec: JobSpec):
    global agent
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not ready")

    return agent.invoke_agent(thread_id=thread_id, resume_url=candidate_info.resume_url, job_desc=job_spec.description)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

    


