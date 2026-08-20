from langchain_core.messages import HumanMessage


test_state{
    "messages" : [
        HumanMessage(
            content = "HI my name is Parth, register number : 5015csc, department : CSE"
        )
    ],
    "student_name" : None,
    "register_no" : None,
    "department" : None,

    "query_category" : " ",
    "kb_context" : " "
}

result = extract_profile(test_state)
print(result)