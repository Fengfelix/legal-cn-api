import os
from uagents_core.utils.registration import (
    register_chat_agent,
    RegistrationRequestCredentials,
)

register_chat_agent(
    "legal-cn-api",
    "http://101.32.245.66:8000/chat",
    active=True,
    credentials=RegistrationRequestCredentials(
        agentverse_api_key=os.environ["AGENTVERSE_KEY"],
        agent_seed_phrase=os.environ["AGENT_SEED_PHRASE"],        
    ),
)
