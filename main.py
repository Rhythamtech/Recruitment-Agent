from utils import extract_candidate_info, llm_score, mock_zoom_meeting, send_email
from typing import Literal,TypedDict
from langgraph.graph import StateGraph, START, END




class EmployeeRecruiterState(TypedDict):
    resume: str | None = None
    resume_url: str | None = None
    job_desc: str | None = None
    parsed_resume: dict | None = None
    analysis: dict | None = None
    decision : Literal["schedule", "reject"] | None = None
    meeting_info: dict | None = None
    email_status: str | None = None

def load_resume(state : EmployeeRecruiterState) -> EmployeeRecruiterState:
    state["resume"] = state["resume_url"]
    return state

def parse_resume(state: EmployeeRecruiterState) -> EmployeeRecruiterState:
    # Use PDFMiner or LLM extraction here
    state["parsed_resume"] = extract_candidate_info(state["resume"])
    return state

def screen_candidate(state: EmployeeRecruiterState) -> EmployeeRecruiterState:
    state["analysis"] = llm_score(state["parsed_resume"], state["job_desc"])
    return state

def decide(state: EmployeeRecruiterState, threshold: float = 5.0) -> EmployeeRecruiterState:
    if (state["analysis"]["score"] or 0) >= threshold:
        state["decision"] = "schedule"
    else:
        state["decision"] = "reject"
    return state

def schedule_interview(state: EmployeeRecruiterState) -> EmployeeRecruiterState:
    state["meeting_info"] = mock_zoom_meeting(state["parsed_resume"]["contact"]["email"])
    return state

def send_invite(state: EmployeeRecruiterState) -> EmployeeRecruiterState:
    state["email_status"] = send_email(candidate_email=state["parsed_resume"]["contact"]["email"], subject="Interview Invitation", body=f"Hi You are selected for interview, {state['meeting_info']}")
    return state

def send_rejection(state: EmployeeRecruiterState) -> EmployeeRecruiterState:
    state["email_status"] = send_email(candidate_email=state["parsed_resume"]["contact"]["email"], subject="Application Update", body=f"Hi You are not selected for interview")
    return state

def make_decision(state: EmployeeRecruiterState) -> Literal["schedule", "reject"]:
    if state["decision"] == "schedule":
        return "schedule"
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

agent = recruit_graph.compile()

final_state = agent.invoke({
    "resume_url": "https://code.ics.uci.edu/wp-content/uploads/2020/06/Resume-Sample-1-Software-Engineer.pdf",
    "job_desc": "Software Engineer"
})

print(final_state)

graph_png_bytes = agent.get_graph(xray=True).draw_mermaid_png()
with open("graph_xray.png", "wb") as f:
    f.write(graph_png_bytes)

