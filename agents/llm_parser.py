"""
agents/llm_parser.py
--------------------
Tool 2: Unstructured text se structured JSON nikalna.

Yeh tera Text Summarizer project jaisa hi hai!
Wahan: text → summary
Yahan: text → structured customer dict

Hum Gemini Flash use karenge (fast + free tier available).
Fallback: HuggingFace pipeline (offline bhi kaam karta hai).
"""

import os
import json
import re
from utils.logger import get_logger

logger = get_logger("llm_parser")

# ─── Prompt Template ────────────────────────────────────────────────────────────
# Yeh prompt LLM ko batata hai kya karna hai.
# {text} mein actual customer text aayega.

EXTRACTION_PROMPT = """You are a data extraction assistant.
Extract customer information from the text below and return ONLY a valid JSON object.
No explanation, no markdown, just raw JSON.

Required fields (use null if not found):
- name: customer full name
- email: email address
- phone: phone number
- company: company name
- plan: product plan they want (Pro/Enterprise/Starter/etc)
- team_size: number of people/seats
- location: city or country
- notes: any special notes or requirements

Text to extract from:
\"\"\"
{text}
\"\"\"

Return only JSON:"""


class LLMParser:
    """
    LLM se unstructured text ko structured JSON mein convert karta hai.

    Supports:
      - Google Gemini (recommended - fast, generous free tier)
      - HuggingFace transformers (offline fallback)
      - Rule-based fallback (agar koi LLM available na ho)
    """

    def __init__(self, provider: str = "gemini"):
        """
        provider: "gemini" | "huggingface" | "mock"
        """
        self.provider = provider
        logger.info(f"🤖 LLM Parser initialized with provider: {provider}")

        if provider == "huggingface":
            self._init_huggingface()

    def _init_huggingface(self):
        """HuggingFace pipeline load karo (tera previous project waala approach)"""
        try:
            from transformers import pipeline
            logger.info("📦 Loading HuggingFace model (flan-t5-base)...")
            # flan-t5 instruction-following mein better hai vs BART
            self.hf_pipeline = pipeline(
                "text2text-generation",
                model="google/flan-t5-base",
                max_new_tokens=300
            )
            logger.info("✅ HuggingFace model loaded!")
        except ImportError:
            logger.error("❌ transformers not installed. Run: pip install transformers")
            raise

    def parse(self, raw_text: str) -> dict:
        """
        Main function: raw text → structured dict

        Returns: dict with customer fields
        """
        logger.info(f"🔍 Parsing text ({len(raw_text)} chars) with {self.provider}...")

        if self.provider == "gemini":
            return self._parse_with_gemini(raw_text)
        elif self.provider == "huggingface":
            return self._parse_with_huggingface(raw_text)
        else:
            return self._parse_mock(raw_text)

    def _parse_with_gemini(self, text: str) -> dict:
        """
        Gemini Flash se parse karo.
        GEMINI_API_KEY env variable mein hona chahiye.
        """
        try:
            import google.generativeai as genai

            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                logger.warning("⚠️  GEMINI_API_KEY not found. Using mock parser.")
                return self._parse_mock(text)

            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")

            prompt = EXTRACTION_PROMPT.format(text=text)
            response = model.generate_content(prompt)
            raw_json = response.text.strip()

            # JSON clean karo (kabhi kabhi LLM ```json ... ``` wrap karta hai)
            raw_json = re.sub(r"```json\n?|```", "", raw_json).strip()

            parsed = json.loads(raw_json)
            logger.info(f"✅ Gemini extracted: {list(parsed.keys())}")
            return parsed

        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON parse failed: {e}. Raw response: {raw_json[:200]}")
            return self._parse_mock(text)  # fallback

        except Exception as e:
            logger.error(f"❌ Gemini error: {e}")
            return self._parse_mock(text)

    def _parse_with_huggingface(self, text: str) -> dict:
        """
        HuggingFace flan-t5 se parse karo.
        Tera text summarizer project ka upgrade!
        """
        prompt = EXTRACTION_PROMPT.format(text=text)
        result = self.hf_pipeline(prompt)
        raw_output = result[0]["generated_text"].strip()

        # JSON extract karne ki koshish karo
        try:
            raw_output = re.sub(r"```json\n?|```", "", raw_output).strip()
            return json.loads(raw_output)
        except json.JSONDecodeError:
            logger.warning("⚠️  HuggingFace output not valid JSON. Using regex fallback.")
            return self._regex_extract(text)

    def _parse_mock(self, text: str) -> dict:
        """
        Demo mode: simple regex se basic fields extract karo.
        No LLM needed — good for testing pipeline without API keys.
        """
        logger.info("🧪 Using rule-based mock parser")
        return self._regex_extract(text)

    def _regex_extract(self, text: str) -> dict:
        """Simple regex patterns se fields nikalo"""

        def find(patterns, default=None):
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    return match.group(1).strip()
            return default

        # Name: "my name is X" ya "from: X" pattern
        name = find([
            r"(?:my name is|name[:\s]+|from[:\s]+)([A-Z][a-z]+ [A-Z][a-z]+)",
            r"Inquiry from[:\s]+([A-Z][a-z]+ [A-Z][a-z]+)",
        ])

        # Email
        email = find([r"([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})"])

        # Phone
        phone = find([r"(\+?\d[\d\s\-]{8,14}\d)"])

        # Company
        company = find([r"[Cc]ompany(?:\s+name)?[:\s]+([^\n.]+)"])

        # Plan
        plan = find([r"(?:plan|tier|subscription)[:\s]+(\w+)", r"(Pro|Enterprise|Starter|Basic|Free)"])

        # Team size
        team_size_raw = find([r"(\d+)\s+(?:user\s+)?seats", r"[Tt]eam\s+size[:\s]+(\d+)", r"(\d+)\s+people"])
        team_size = int(team_size_raw) if team_size_raw else None

        result = {
            "name": name,
            "email": email,
            "phone": phone,
            "company": company,
            "plan": plan,
            "team_size": team_size,
            "location": None,
            "notes": None,
        }

        logger.info(f"✅ Regex extracted: name={name}, email={email}, plan={plan}")
        return result
