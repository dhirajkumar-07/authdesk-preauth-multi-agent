"""Run this first after adding your key: python check_llm.py"""
import asyncio
from app import llm
print(llm.mode())
if llm.available(): print(asyncio.run(llm.ask_json("Reply with {\"ok\": true}", "ping")))
else: print("No API key found. Put GEMINI_API_KEY in .env")
