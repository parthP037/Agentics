from models import llm
from state.university_state import University_state
import json
def extractor_profile(state:University_state)->University_state:
    """
    Detects if the user mentioned their name, register number, or department.
    Updates state fields if found.
    """
    last_msg = state["messages"][-1].content
    prompt = (
        "Extract the student profile info from this message.\n"
        "Message: \""+last_msg+"\" \n\n"
        "Respond with ONLY valid JSON:\n"
        "{\"name\":null, \"register_no\":null, \"department\":null}"
    )
    result = llm.invoke(prompt)
    raw = result.content.strip().replace("```json","").replace("```", "").strip()

    try:
        extracted = json.loads(raw)

        if extracted.get("name") and not state.get("student_name"):
            state["student_name"] = extracted["name"]
        if extracted.get("register_no") and not state.get("register_no"):
            state["registor_no"] = extracted["register_no"]
        if extracted.get("department") and not state.get("deparment"):
            state["department"] = extracted["department"]

{
    "name" : "kaviya",
    "register" : "null",
    "dep" : "cse"
}