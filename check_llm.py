import os, sys
# Add authdesk-kit subfolder to path
subfolder = os.path.join(os.path.dirname(__file__), "authdesk-kit")
if os.path.exists(subfolder):
    sys.path.insert(0, subfolder)
    os.chdir(subfolder)

from app import llm
import asyncio
print(llm.mode())
if llm.available(): print(asyncio.run(llm.ask_json("Reply with {\"ok\": true}", "ping")))
else: print("No API key found. Put GEMINI_API_KEY in .env")

