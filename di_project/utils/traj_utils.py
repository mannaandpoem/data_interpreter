def format_trajs(working_memory, full_trajs: bool = True):
    messages = working_memory.get()
    all_context = ""
    if full_trajs:
        for i, message in enumerate(messages, 1):
            message = str(message)
            role = message.split(":")[0]
            content = ":".join(message.split(":")[1:])
            all_context += f"{role} - Round {i // 2}: {content}\n\n"
    else:
        user = "user"
        assistant = "assistant"
        msg_size = len(messages) - 1
        for i, message in enumerate(messages, 1):
            message = str(message)
            split_idx = message.find(": ")
            role = message[:split_idx]
            content = message[split_idx + 2 :]
            content = content.strip("\n")

            round_id = i // 2
            round_tag = f"Round_{round_id}"
            if role == user:
                if msg_size - i >= 2 and i != 1:
                    user_content = (
                        f"    <{user}>\n" + "For earlier rounds, Observation is not displayed" + f"\n    </{user}>\n"
                    )
                else:
                    user_content = f"    <{user}>\n" + content + f"\n    </{user}>\n"

                if round_id == 0:
                    all_context = f"<{round_tag}>\n" + user_content.strip("\n") + f"\n</{round_tag}>\n"
                if round_id > 0:
                    all_context += user_content.strip("\n") + f"\n</{round_tag}>\n"
            elif role == assistant:
                ass_content = f"    <{assistant}>\n" + content + f"\n    </{assistant}>\n"
                all_context += f"<{round_tag}>\n" + ass_content

    return all_context
