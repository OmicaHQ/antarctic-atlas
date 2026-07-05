from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
PDF_FILENAME = "Reviews of Geophysics - 2020 - Noble - The Sensitivity of the Antarctic Ice Sheet to a Changing Climate  Past  Present  and.pdf"
PDF_PATH = BASE_DIR / PDF_FILENAME

OLLAMA_URL = "http://127.0.0.1:11434"
OLLAMA_MODEL = "gemma4:e4b"

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-v4-pro"

OPENAI_BASE_URL = "https://api.openai.com/v1"
OPENAI_MODEL = "gpt-4o"
OPENAI_MODEL_OPTIONS = ["gpt-4o", "gpt-4.1"]
