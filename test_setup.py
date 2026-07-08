"""
Phase 1 test script.
This does ONE thing: sends a prompt to your local Llama 3 (via Ollama)
through LangChain, and prints the reply.

If this script works, it proves three things are correctly connected:
1. Ollama is running and serving the llama3.2 model
2. langchain-ollama can talk to it
3. Your Python environment has the right packages installed

Run this with: python test_setup.py
"""

from langchain_ollama import OllamaLLM

def main():
    print("Connecting to Llama 3.2 via Ollama...")

    # This creates a connection to your locally running Ollama server.
    # 'model="llama3.2"' must match the exact name Ollama shows when you run:
    #   ollama list
    llm = OllamaLLM(model="llama3.2")

    prompt = "In one sentence, explain what a multi-agent AI system is."
    print(f"\nSending prompt: {prompt}\n")

    response = llm.invoke(prompt)

    print("Llama 3.2 replied:\n")
    print(response)
    print("\nSetup check passed. You're ready for Phase 2.")

if __name__ == "__main__":
    main()