"""
============================================================
src/ai_engine/ollama_client.py
------------------------------------------------------------
PURPOSE:
    Low-level client for communicating with the local Ollama server.
    All AI features (ATS matching, resume writing, cover letters)
    use this client to talk to local AI models.

WHAT IS OLLAMA?
    Ollama is a free, open-source tool that lets you run large
    language models (LLMs) 100% locally on your computer.
    - No internet required once model is downloaded
    - No API keys needed
    - No cost ever
    - Data stays on your machine

HOW IT WORKS:
    1. Ollama runs as a local server on port 11434
    2. We send text prompts to it via HTTP
    3. It runs the AI model and streams back the response
    4. We collect and return the full response text

SUPPORTED MODELS:
    - qwen2.5     (recommended: good at coding/analysis)
    - llama3      (Meta's model, also excellent)
    - mistral     (fast, efficient)
    - phi3        (Microsoft, compact and capable)
    - gemma2      (Google's model)
============================================================
"""

import json                 # Parse JSON responses
import requests             # HTTP communication with Ollama
from loguru import logger   # Logging
from typing import Optional


class OllamaClient:
    """
    Client for the local Ollama AI server.

    Handles all communication with the Ollama API.
    Provides simple methods to generate text from prompts.
    """

    def __init__(self, config: dict):
        """
        Initialize the Ollama client.

        Args:
            config: Config dict from config.yaml
        """
        ollama_cfg = config.get('ollama', {})

        # Ollama server URL (default: localhost:11434)
        self.base_url = ollama_cfg.get('base_url', 'http://localhost:11434')

        # The model to use (e.g., 'qwen2.5', 'llama3')
        self.model = ollama_cfg.get('model', 'qwen2.5')

        # Maximum seconds to wait for AI response
        self.timeout = ollama_cfg.get('timeout', 120)

        # Temperature: 0.0 = deterministic, 1.0 = creative
        self.temperature = ollama_cfg.get('temperature', 0.7)

        # API endpoint for text generation
        self.api_url = f"{self.base_url}/api/generate"

        logger.info(f"OllamaClient: using model '{self.model}' at {self.base_url}")

    def is_available(self) -> bool:
        """
        Checks if the Ollama server is running and accessible.
        Call this before any AI operations to give helpful errors.

        Returns:
            True if Ollama is running, False otherwise.
        """
        try:
            # Try to hit the root endpoint
            response = requests.get(
                f"{self.base_url}/api/tags",  # Lists installed models
                timeout=5
            )
            return response.status_code == 200
        except requests.exceptions.ConnectionError:
            return False
        except Exception:
            return False

    def list_models(self) -> list[str]:
        """
        Returns list of models installed in Ollama.

        Returns:
            List of model name strings.
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=10)
            data = response.json()
            models = data.get('models', [])
            return [m['name'] for m in models]
        except Exception as e:
            logger.error(f"Failed to list Ollama models: {e}")
            return []

    def generate(self, prompt: str, system_prompt: str = None, stream: bool = False) -> str:
        """
        Sends a prompt to the Ollama model and returns the response.

        This is the CORE method used by all AI features.

        Args:
            prompt: The user's question/request to the AI.
            system_prompt: Optional system-level instructions that
                          define the AI's role/behavior.
            stream: If True, stream response token by token.
                    If False (default), wait for full response.

        Returns:
            The AI's full response as a string.
            Returns empty string if request fails.

        Example:
            response = client.generate(
                prompt="Analyze this job description: ...",
                system_prompt="You are an ATS expert."
            )
        """
        # Check if Ollama is running
        if not self.is_available():
            logger.error(
                "Ollama is NOT running! Start it with: ollama serve\n"
                "Then download a model: ollama pull qwen2.5"
            )
            return "ERROR: Ollama is not running. Please start Ollama first."

        # Build the request payload
        payload = {
            "model": self.model,          # Which model to use
            "prompt": prompt,             # The user's input
            "stream": False,              # Get all at once (easier to handle)
            "options": {
                "temperature": self.temperature,
                "num_predict": 4096,      # Max tokens in response
                "top_p": 0.9,             # Nucleus sampling
            }
        }

        # Add system prompt if provided
        if system_prompt:
            payload["system"] = system_prompt

        try:
            logger.debug(f"Sending prompt to Ollama ({len(prompt)} chars)...")

            # Make the HTTP POST request to Ollama
            response = requests.post(
                self.api_url,
                json=payload,             # Send as JSON
                timeout=self.timeout      # Don't wait forever
            )

            # Raise exception for HTTP errors
            response.raise_for_status()

            # Parse the JSON response
            result = response.json()

            # Extract the AI's response text
            ai_response = result.get('response', '').strip()

            if not ai_response:
                logger.warning("Ollama returned empty response")
                return ""

            logger.debug(f"Ollama response received ({len(ai_response)} chars)")
            return ai_response

        except requests.exceptions.Timeout:
            logger.error(
                f"Ollama timed out after {self.timeout}s. "
                "Try: increasing timeout in config.yaml, or using a smaller model."
            )
            return "ERROR: AI request timed out. Try a smaller model or increase timeout."

        except requests.exceptions.ConnectionError:
            logger.error("Lost connection to Ollama server")
            return "ERROR: Cannot connect to Ollama. Run: ollama serve"

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Ollama response: {e}")
            return "ERROR: Invalid response from Ollama."

        except Exception as e:
            logger.error(f"Unexpected Ollama error: {e}")
            return f"ERROR: {str(e)}"

    def generate_structured(self, prompt: str, system_prompt: str = None) -> dict:
        """
        Generates a response expected to be valid JSON.
        Automatically attempts to parse the JSON output.

        Useful when asking the AI to return structured data
        like ATS scores, skill lists, etc.

        Args:
            prompt: The prompt (should ask AI to return JSON).
            system_prompt: System role instructions.

        Returns:
            Parsed JSON dict, or {'error': ..., 'raw': ...} on failure.
        """
        # Ask for JSON output in the prompt
        json_prompt = prompt + "\n\nIMPORTANT: Respond with ONLY valid JSON. No other text."

        raw_response = self.generate(json_prompt, system_prompt)

        # Try to extract JSON from the response
        try:
            # Sometimes the model wraps JSON in markdown code blocks
            # Remove ```json ... ``` markers if present
            cleaned = raw_response.strip()
            if cleaned.startswith('```'):
                # Remove first and last lines (code block markers)
                lines = cleaned.split('\n')
                cleaned = '\n'.join(lines[1:-1])

            return json.loads(cleaned)

        except json.JSONDecodeError:
            # If JSON parsing fails, try to find JSON within the text
            try:
                import re
                # Look for JSON object pattern
                match = re.search(r'\{.*\}', raw_response, re.DOTALL)
                if match:
                    return json.loads(match.group())
            except Exception:
                pass

            logger.warning("AI did not return valid JSON. Returning raw text.")
            return {'error': 'Invalid JSON response', 'raw': raw_response}
