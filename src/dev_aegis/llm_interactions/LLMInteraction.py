import requests
import json
import sys

class LLMInteraction:
    """
    A class to handle interaction with a local Ollama LLM instance.
    """
    def __init__(self, model='deepseek-coder:6.7b', host='http://localhost:11434'):
        """
        Initializes the LLMInteraction class.

        Args:
            model (str): The name of the model to use in Ollama (e.g., 'deepseek-coder:6.7b').
            host (str): The URL of the Ollama server.
        """
        self.model = model
        self.host = host
        self.api_url = f"{self.host}/api/generate"

    def _check_server_status(self):
        """
        Checks if the Ollama server is running.
        """
        try:
            response = requests.get(self.host, timeout=5)
            response.raise_for_status()
            return True
        except requests.RequestException:
            print(f"ERROR: Could not connect to Ollama server at '{self.host}'.")
            print("Please ensure Ollama is running.")
            return False

    def get_response(self, prompt):
        """
        Sends a prompt to the Ollama model and gets a response.

        Args:
            prompt (str): The user's prompt to send to the model.

        Returns:
            str: The model's response, or an error message if something went wrong.
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False  # We want the full response at once
        }
        try:
            response = requests.post(self.api_url, json=payload)
            response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

            # The response from Ollama is a JSON object
            response_data = response.json()
            return response_data.get('response', 'No response field in the answer.')

        except requests.exceptions.HTTPError as http_err:
            return f"HTTP error occurred: {http_err}"
        except requests.exceptions.ConnectionError as conn_err:
            return f"Connection error occurred: {conn_err}"
        except requests.exceptions.Timeout as timeout_err:
            return f"Timeout error occurred: {timeout_err}"
        except requests.exceptions.RequestException as req_err:
            return f"An unexpected error occurred: {req_err}"

    def start_chat(self):
        """
        Starts an interactive command-line chat session with the LLM.
        """
        if not self._check_server_status():
            sys.exit(1)

        print("--- Ollama Chat Interface ---")
        print(f"Model: {self.model}")
        print("Type 'exit' or 'quit' to end the session.")
        print("-" * 30)

        while True:
            try:
                prompt = input("You: ")
                if prompt.lower() in ['exit', 'quit']:
                    print("Exiting chat. Goodbye!")
                    break

                print("Bot: Thinking...", end='\r')
                response = self.get_response(prompt)
                # Clear the "Thinking..." line and print the response
                print(f"Bot: {response}      ")

            except KeyboardInterrupt:
                print("\nExiting chat. Goodbye!")
                break

def main():
    """
    Main function to initialize and run the LLM chat.
    """
    # You can change the model here if you have a different one pulled in Ollama
    # For your request, we are using 'deepseek-coder:6.7b'
    llm_chat = LLMInteraction(model='deepseek-r1:8b')
    llm_chat.start_chat()

if __name__ == "__main__":
    main()
