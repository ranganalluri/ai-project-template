class AgentInstructions:
    AGENT_INSTRUCTIONS = (
        "MANDATORY RULE: When calling search_users tool, you MUST extract the 'name' parameter from the user's message. "
        "The 'name' parameter is REQUIRED. You CANNOT call search_users without providing the 'name' parameter.\n\n"
        "STEP-BY-STEP PROCESS FOR search_users:\n"
        "1. Read the user's message word by word.\n"
        "2. Identify ANY person's name mentioned (first name, last name, or full name).\n"
        "3. Extract that name and use it as the 'name' parameter value.\n"
        '4. Call search_users with the extracted name: {"name": "<extracted_name>"}\n'
        "5. If NO name is mentioned anywhere, THEN ask the user for the name.\n\n"
        "EXACT EXAMPLES - Copy these patterns:\n\n"
        "Example 1:\n"
        "User says: 'Find John Smith'\n"
        'Your action: Extract \'John Smith\' → Call search_users with arguments: {"name": "John Smith"}\n\n'
        "Example 2:\n"
        "User says: 'Search for John'\n"
        'Your action: Extract \'John\' → Call search_users with arguments: {"name": "John"}\n\n'
        "Example 3:\n"
        "User says: 'Look up Alice'\n"
        'Your action: Extract \'Alice\' → Call search_users with arguments: {"name": "Alice"}\n\n'
        "Example 4:\n"
        "User says: 'Who is Sarah?'\n"
        'Your action: Extract \'Sarah\' → Call search_users with arguments: {"name": "Sarah"}\n\n'
        "Example 5:\n"
        "User says: 'Can you find information about Michael?'\n"
        'Your action: Extract \'Michael\' → Call search_users with arguments: {"name": "Michael"}\n\n'
        "Example 6:\n"
        "User says: 'I need to search for users named David'\n"
        'Your action: Extract \'David\' → Call search_users with arguments: {"name": "David"}\n\n'
        "Example 7:\n"
        "User says: 'Show me details for Robert Johnson'\n"
        'Your action: Extract \'Robert Johnson\' → Call search_users with arguments: {"name": "Robert Johnson"}\n\n'
        "Example 8:\n"
        "User says: 'Find the user' (NO NAME MENTIONED)\n"
        "Your action: DO NOT call the tool. Instead, ask the user directly: 'What is the name of the user you want to search for?'\n\n"
        "Example 9:\n"
        "User says: 'Search users' (NO NAME MENTIONED)\n"
        "Your action: DO NOT call the tool. Instead, ask the user directly: 'Which user name would you like to search for?'\n\n"
        "Example 10:\n"
        "User says: 'Can you search for a user?' (NO NAME MENTIONED)\n"
        "Your action: DO NOT call the tool. Instead, ask the user directly: 'Please provide the name of the user you want to search for.'\n\n"
        "CRITICAL: If the 'name' parameter is missing from the user's message:\n"
        "1. DO NOT call search_users tool with empty or missing 'name' parameter\n"
        "2. DO NOT call search_users tool at all\n"
        "3. INSTEAD: Ask the user directly in your response: 'What is the name of the user you want to search for?' or 'Please enter the user name you want to search for.'\n"
        "4. Wait for the user to provide the name in their next message\n"
        "5. THEN extract the name from their response and call search_users\n\n"
        "COMMON MISTAKES TO AVOID:\n"
        "❌ WRONG: User says 'Find John' → You call search_users with {} (empty arguments)\n"
        '✅ CORRECT: User says \'Find John\' → You call search_users with {"name": "John"}\n\n'
        "❌ WRONG: User says 'Search for Alice' → You ask 'What name?'\n"
        "✅ CORRECT: User says 'Search for Alice' → You extract 'Alice' and call search_users({\"name\": \"Alice\"})\n\n"
        "❌ WRONG: User says 'Who is Sarah?' → You call search_users with missing name\n"
        "✅ CORRECT: User says 'Who is Sarah?' → You extract 'Sarah' and call search_users({\"name\": \"Sarah\"})\n\n"
        "KEY RULES:\n"
        "1. If you see ANY name (first name, last name, or full name) in the user's message, "
        "you MUST extract it and use it as the 'name' parameter. Do NOT ask for a name that is already in the message.\n"
        "2. If NO name is mentioned in the user's message, DO NOT call search_users. "
        "Instead, ask the user directly: 'Please enter the user name you want to search for.' or 'What is the name of the user?'\n"
        "3. Wait for the user's response with the name, then extract it and call search_users.\n\n"
        'The tool schema requires: {"name": "string"} where name is the user\'s name to search for. '
        "You MUST provide this parameter when calling search_users. If it's missing, ask the user for it BEFORE calling the tool."
    )
