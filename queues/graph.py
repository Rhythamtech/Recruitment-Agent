import os
import datetime
from dotenv import load_dotenv
from typing import Literal,TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.mongodb import MongoDBSaver
from utils import extract_candidate_info, llm_score, mock_zoom_meeting, send_email

load_dotenv()


class EmployeeRecruiterState(TypedDict):
    resume: str | None = None
    resume_url: str | None = None
    job_desc: str | None = None
    parsed_resume: dict | None = None
    analysis: dict | None = None
    decision : Literal["schedule", "reject"] | None = None
    meeting_info: dict | None = None
    email_status: str | None = None
    status : str | None = None


def load_resume(state : EmployeeRecruiterState) -> EmployeeRecruiterState:
    state["resume"] = state["resume_url"]
    state["status"] = "Loading resume"
    return state

def parse_resume(state: EmployeeRecruiterState) -> EmployeeRecruiterState:
    # Use PDFMiner or LLM extraction here
    state["parsed_resume"] = extract_candidate_info(state["resume"])
    state["status"] = "Parsed resume data"
    return state

def screen_candidate(state: EmployeeRecruiterState) -> EmployeeRecruiterState:
    state["analysis"] = llm_score(state["parsed_resume"], state["job_desc"])
    state["status"] = "Screened candidate data"
    return state

def decide(state: EmployeeRecruiterState, threshold: float = 6.0) -> EmployeeRecruiterState:
    if (float(state["analysis"]["score"]) or 0) >= threshold:
        state["decision"] = "schedule"
        state["status"] = "Decided to schedule interview"
    else:
        state["decision"] = "reject"
        state["status"] = "Decided to reject"
    return state

def schedule_interview(state: EmployeeRecruiterState) -> EmployeeRecruiterState:
    """
    As, a sample of business logic. We schedule new interview for the candidate.
    Every Friday : 1:30 pm IST
    """
    time = datetime.datetime.now()
    
    days_until_friday = (4 - time.weekday() + 7) % 7  # Friday is 4
    next_friday = time.date.today() + datetime.timedelta(days=days_until_friday)
    
    # Set the meeting time to 1:30 PM IST (UTC+5:30)
    meeting_time_ist = datetime.datetime.combine(next_friday, datetime.time(13, 30))
    
    # Convert to a more general format if needed, or keep as is
    formatted_time = meeting_time_ist.strftime("%Y-%m-%d %H:%M IST")


    state["meeting_info"] = mock_zoom_meeting(email = state["parsed_resume"]["contact"]["email"], 
                                              name = state["parsed_resume"]["name"], 
                                              meeting_time=formatted_time)
    state["status"] = "Scheduled interview"
    return state
            

def send_invite(state: EmployeeRecruiterState) -> EmployeeRecruiterState:
    subject = "Interview Invitation"
    meet_details = f"""
                   Meeting Link: {state['meeting_info']['meeting_link']}
                   Meeting Time: {state['meeting_info']['meeting_time']}
                   Meeting ID: {state['meeting_info']['meeting_id']}
                   """
    body = f"Hi You are selected for interview, here is your meeting info: {meet_details}"
    receiver_mail = state["parsed_resume"]["contact"]["email"]
    
    state["email_status"] = send_email(candidate_email=receiver_mail, subject=subject, body=body)
    state["status"] = "Sent interview invitation"
    return state

def send_rejection(state: EmployeeRecruiterState) -> EmployeeRecruiterState:
    subject = "Application Update"
    body = "Hi You are not selected for interview"
    receiver_mail = state["parsed_resume"]["contact"]["email"]
    
    state["email_status"] = send_email(candidate_email=receiver_mail, subject=subject, body=body)
    state["status"] = "Sent rejection email"
    return state

def make_decision(state: EmployeeRecruiterState) -> Literal["schedule", "reject"]:
    if state["decision"] == "schedule":
        return "invite"
    else:
        return "reject"
            
recruit_graph = StateGraph(EmployeeRecruiterState)
recruit_graph.add_node("load", load_resume)
recruit_graph.add_node("parse", parse_resume)
recruit_graph.add_node("screen", screen_candidate)
recruit_graph.add_node("decide", decide)
recruit_graph.add_node("schedule", schedule_interview)
recruit_graph.add_node("invite", send_invite)
recruit_graph.add_node("reject", send_rejection)


recruit_graph.add_edge(START, "load")
recruit_graph.add_edge("load", "parse")
recruit_graph.add_edge("parse", "screen")
recruit_graph.add_edge("screen", "decide")
recruit_graph.add_conditional_edges("decide", make_decision)
recruit_graph.add_edge("schedule", "invite")
recruit_graph.add_edge("invite", END)
recruit_graph.add_edge("reject", END)


class EmployeeRecruiterAgent:
    def __init__(self,checkpointer: MongoDBSaver | None = None):
        self.checkpointer = checkpointer
        self.agent = None
        if not self.checkpointer:
            self.checkpointer = MongoDBSaver.from_conn_string(os.getenv("MONGODB_URI"))

        self.build_graph(checkpointer=checkpointer)

    def build_graph(self,checkpointer: MongoDBSaver | None = None): 
        self.checkpointer = checkpointer
        self.agent = recruit_graph.compile(checkpointer=checkpointer)


    def invoke_agent(self, thread_id: str, resume_url: str, job_desc: str):
        config = {
            "configurable": {
                "thread_id": thread_id
            }
        }

        return self.agent.invoke({"resume_url": resume_url,
            "job_desc": job_desc},
            config=config)



    def stream_agent(self, thread_id: str, resume_url: str, job_desc: str):
        config = {
            "configurable": {
                "thread_id": thread_id
            }
        }

        try :
            for chunk in self.agent.stream({"resume_url": resume_url,
                "job_desc": job_desc},
                config=config,
                stream_mode= 'values'):
                if "status" in chunk:
                    yield chunk
            
        except Exception as e:
            yield {"error": str(e)}

def run_agent_workflow(thread_id: str, resume_url: str, job_desc: str):
    agent = EmployeeRecruiterAgent()
    return agent.invoke_agent(thread_id=thread_id, resume_url=resume_url, job_desc=job_desc)
