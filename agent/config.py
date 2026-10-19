"""Pinned experiment configuration. Change these only on purpose and record why.

Ollama is only the runtime. The model is Meta Llama 3.1 8B Instruct, Q4_K_M quantization,
pulled from the Ollama library under the tag below. The digest is what the Ollama library
lists for that tag; the harness checks it at startup and records the digest it actually saw.
"""
import os

MODEL_TAG = os.environ.get("OLLAMA_MODEL", "llama3.1:8b-instruct-q4_K_M")
MODEL_DIGEST = "46e0c10c039e"
MODEL_DESCRIPTION = "Meta Llama 3.1 8B Instruct, Q4_K_M quantization"

# Sampling settings used for every real-model trial. A per-trial seed is added by the harness.
DEFAULT_OPTIONS = {"temperature": 0.8, "num_ctx": 4096}

# Hard cap on model/tool round trips for one email.
MAX_STEPS = 6
