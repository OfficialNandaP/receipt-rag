import json
import os
import traceback
from abc import ABC

import requests


class BaseLLM(ABC):

    def __init__(self, *args, **kwargs):
        pass

    def generate(self, prompt: str, **kwargs):
        raise NotImplementedError

    def chat(self, prompt: str, **kwargs):
        raise NotImplementedError


class GeminiLLM(BaseLLM):
    def __init__(self, *args, **kwargs):
        """Initialize the Gemini language model.
        - api_key: str: The API key for the Gemini API.
        """
        super().__init__(*args, **kwargs)
        try:
            import google.generativeai as genai
        except ImportError as error:
            raise ImportError("Install google-generativeai to use Gemini") from error
        self._genai = genai
        GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or kwargs.get("api_key")
        if not GOOGLE_API_KEY:
            raise ValueError(
                "Please set GOOGLE_API_KEY environment variable or set api_key."
            )
        genai.configure(api_key=GOOGLE_API_KEY)
        generation_config = genai.GenerationConfig(
            temperature=0.0,
        )
        self.model = genai.GenerativeModel(
            "text-davinci-003", generation_config=generation_config
        )

    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text from the model.
        - prompt: str: The prompt to generate text from.
        - retried: int: The number of times the request has been retried.
        """
        retried = kwargs.get("retried", 0)
        if retried < 0:
            raise Exception("Retried too many times.")
        try:
            response = self.model.generate_content(prompt)
            if response.candidates and response.candidates[0].content.parts:
                return response.candidates[0].content.parts[0].text
            else:
                return response.text
        except Exception as error:
            if error.__class__.__name__ == "InternalServerError":
                print("Retrying 500...", retried)
                return self.generate(prompt, retried=retried - 1)
            print("An error occurred!")
            traceback.print_exc()
            kwargs["retried"] = retried - 1
            return self.generate(prompt, **kwargs)

    def chat(self, prompt: str, **kwargs) -> str:
        return self.generate(prompt, **kwargs)


class OllamaLLM(BaseLLM):
    def __init__(self, *args, **kwargs):
        """Initialize the Ollama language model.
        - base_url: str: The base URL of the Ollama API.
        - model_name: str: The name of the model to use.
        """
        super().__init__(*args, **kwargs)
        self.base_url = kwargs.get("base_url", "http://localhost:11434")
        self.model_name = kwargs.get("model_name")
        if not self.model_name:
            raise ValueError("Please provide a model_name.")

    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text from the model.
        - prompt: str: The prompt to generate text from.
        - model_name: str: The name of the model to use.
        - stream: bool: Whether to stream the response.
        - format: str: The format of the response.
        - timeout: int: The timeout for the request.
        """
        retried = kwargs.get("retried", 0)
        if retried < 0:
            raise Exception("Giving up after several retries.")
        try:
            data = {
                "model": kwargs.get("model_name", self.model_name),
                "prompt": prompt,
                "stream": kwargs.get("stream", False),
                "format": kwargs.get("format"),
            }
            response = requests.post(
                url=self.base_url + "/api/generate",
                data=json.dumps(data),
                timeout=kwargs.get("timeout", 60),
            )
            response.raise_for_status()
            if format == "json":
                return json.loads(response.json()["response"])
            return response.json()["response"]
        except json.decoder.JSONDecodeError:
            kwargs["retried"] = retried - 1
            return self.generate(prompt, **kwargs)
        except Exception:
            kwargs["retried"] = retried - 1
            return self.generate(prompt, **kwargs)

    def chat(self, prompt: str, **kwargs) -> str:
        # We don't have a plan to implement chat for Ollama.
        raise NotImplementedError


class AzureOpenAILLM(BaseLLM):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        endpoint = (kwargs.get("endpoint") or os.getenv("AZURE_OPENAI_ENDPOINT") or "").strip().rstrip("/")
        api_key = (kwargs.get("api_key") or os.getenv("AZURE_OPENAI_API_KEY") or "").strip()
        deployment = (kwargs.get("deployment_name") or os.getenv("AZURE_OPENAI_DEPLOYMENT") or "").strip()
        api_version = (kwargs.get("api_version") or os.getenv("AZURE_OPENAI_API_VERSION") or "").strip()
        if not all((endpoint, api_key, deployment, api_version)):
            raise ValueError(
                "Set AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, "
                "AZURE_OPENAI_DEPLOYMENT, and AZURE_OPENAI_API_VERSION."
            )
        try:
            from openai import AzureOpenAI, OpenAI
        except ImportError as error:
            raise ImportError("Install the openai package to use Azure OpenAI") from error
        self.deployment = deployment
        self.endpoint = endpoint
        self.is_openai_v1_endpoint = endpoint.lower().endswith("/openai/v1")
        self.is_foundry_project = ".services.ai.azure.com" in endpoint.lower()
        if self.is_openai_v1_endpoint or self.is_foundry_project:
            base_url = endpoint.rstrip("/")
            if not base_url.endswith("/openai/v1"):
                base_url += "/openai/v1"
            self.client = OpenAI(api_key=api_key, base_url=base_url + "/")
        else:
            self.client = AzureOpenAI(
                azure_endpoint=endpoint,
                api_key=api_key,
                api_version=api_version,
            )

    def generate(self, prompt: str, **kwargs) -> str:
        try:
            request = {
                "model": self.deployment,
                "messages": [{"role": "user", "content": prompt}],
            }
            if self.is_openai_v1_endpoint or self.is_foundry_project:
                request["max_completion_tokens"] = kwargs.get(
                    "max_completion_tokens", kwargs.get("max_tokens", 1200)
                )
            else:
                request["temperature"] = kwargs.get("temperature", 0.0)
                request["max_tokens"] = kwargs.get("max_tokens", 1200)
            if kwargs.get("response_format") and not (self.is_openai_v1_endpoint or self.is_foundry_project):
                request["response_format"] = kwargs["response_format"]
            print(
                "[AzureOpenAI] request "
                f"endpoint={self.endpoint} deployment={self.deployment} "
                f"mode={'openai-v1' if self.is_openai_v1_endpoint or self.is_foundry_project else 'azure'} "
                f"body={json.dumps(request, default=str)[:1000]}",
                flush=True,
            )
            response = self.client.chat.completions.create(**request)
            content = response.choices[0].message.content if response.choices else None
            if not content:
                raise RuntimeError("Azure OpenAI returned an empty response")
            print(f"[AzureOpenAI] response={content[:2000]}", flush=True)
            return content
        except Exception as error:
            print(f"[AzureOpenAI] error={error}", flush=True)
            if "DeploymentNotFound" in str(error) or "deployment does not exist" in str(error):
                raise RuntimeError(
                    "Azure OpenAI deployment not found. Set AZURE_OPENAI_DEPLOYMENT "
                    f"to the exact deployment name configured for {self.endpoint}. "
                    f"Current value: {self.deployment!r}."
                ) from error
            raise RuntimeError(f"Azure OpenAI request failed: {error}") from error

    def chat(self, prompt: str, **kwargs) -> str:
        return self.generate(prompt, **kwargs)
