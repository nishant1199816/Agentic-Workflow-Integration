"""
agents/orchestrator.py
-----------------------
Yeh hai system ka "brain" — the Orchestrator Agent.

Kya karta hai?
  1. S3 se file list lo (S3Ingestor use karo)
  2. Har file ke liye:
     a. File content padhо (S3Ingestor)
     b. LLM se structured data nikalo (LLMParser)
     c. CRM mein data daalo (CRMUpdater)
  3. Results track karo — success kitne, fail kitne
  4. Final summary print karo

"Agentic" kyon hai yeh?
  - Agent decide karta hai tool calling ka sequence
  - Agar ek step fail ho, toh error handle karta hai
  - Parallel ya sequential processing choose kar sakta hai
  - Future mein: LLM agent decide kare ki kab kaunsa tool call kare
"""

from agents.s3_ingestor import S3Ingestor
from agents.llm_parser import LLMParser
from agents.crm_updater import CRMUpdater
from utils.logger import get_logger

logger = get_logger("orchestrator")


class OnboardingOrchestrator:
    """
    Main orchestrator — saare tools ko coordinate karta hai.

    Design pattern: Tool-use Agent
      - Agent ke paas 3 tools hain (S3, LLM, CRM)
      - Har file ke liye ek "episode" run hota hai
      - Episode mein tools sequentially call hote hain
    """

    def __init__(
        self,
        bucket_name: str = "onboarding-bucket",
        llm_provider: str = "mock",   # "gemini" | "huggingface" | "mock"
        mock_mode: bool = True,        # True = local testing, False = real APIs
    ):
        logger.info("=" * 60)
        logger.info("🚀 Initializing Onboarding Orchestrator Agent")
        logger.info("=" * 60)

        # Tool 1: S3 Ingestor
        self.s3 = S3Ingestor(bucket_name=bucket_name, mock_mode=mock_mode)

        # Tool 2: LLM Parser
        self.parser = LLMParser(provider=llm_provider)

        # Tool 3: CRM Updater
        self.crm = CRMUpdater(mock_mode=mock_mode)

        # Results track karne ke liye
        self.results = {
            "processed": 0,
            "success": 0,
            "failed": 0,
            "details": []
        }

    def run(self) -> dict:
        """
        Full pipeline run karo.

        Flow:
          S3 file list → for each file → ingest → parse → CRM update
        """
        logger.info("\n📋 Step 1: Fetching file list from S3...")
        file_keys = self.s3.list_files()

        if not file_keys:
            logger.warning("⚠️  No files found in S3. Nothing to process.")
            return self.results

        logger.info(f"\n🔄 Step 2: Processing {len(file_keys)} files...\n")

        for i, file_key in enumerate(file_keys, 1):
            logger.info(f"\n{'─' * 40}")
            logger.info(f"📁 File {i}/{len(file_keys)}: {file_key}")
            logger.info(f"{'─' * 40}")

            self._process_single_file(file_key)

        self._print_summary()
        return self.results

    def _process_single_file(self, file_key: str):
        """
        Ek file ke liye poora pipeline run karo.
        Har step ka error alag se catch karo — ek fail se poora system na ruke.
        """
        self.results["processed"] += 1
        file_result = {"file": file_key, "status": "pending", "customer": None, "crm_id": None}

        try:
            # ── Step A: S3 se file content padhо ──────────────────────────────
            logger.info("📥 [Tool 1] Ingesting from S3...")
            raw_text = self.s3.read_file(file_key)

            # ── Step B: LLM se structured data nikalo ─────────────────────────
            logger.info("🤖 [Tool 2] Parsing with LLM...")
            customer_data = self.parser.parse(raw_text)

            # Validate: email nahi toh CRM mein daalna mushkil hai
            if not customer_data.get("email"):
                raise ValueError(f"No email found in '{file_key}'. Cannot update CRM.")

            logger.info(f"📊 Extracted: {_format_customer(customer_data)}")

            # ── Step C: CRM mein data daalo ────────────────────────────────────
            logger.info("📤 [Tool 3] Updating CRM...")
            crm_response = self.crm.create_or_update_customer(customer_data)

            # ── Success ────────────────────────────────────────────────────────
            file_result["status"] = "success"
            file_result["customer"] = customer_data
            file_result["crm_id"] = crm_response.get("id")
            self.results["success"] += 1
            logger.info(f"🎉 Successfully onboarded: {customer_data.get('email')}")

        except ValueError as e:
            # Data quality issue (missing email etc.)
            logger.error(f"❌ Data validation error: {e}")
            file_result["status"] = "failed"
            file_result["error"] = str(e)
            self.results["failed"] += 1

        except Exception as e:
            # API error, network error, ya retry limit exceed
            logger.error(f"❌ Pipeline error for '{file_key}': {e}")
            file_result["status"] = "failed"
            file_result["error"] = str(e)
            self.results["failed"] += 1

        self.results["details"].append(file_result)

    def _print_summary(self):
        """Final summary print karo"""
        r = self.results
        logger.info(f"\n{'=' * 60}")
        logger.info("📊 PIPELINE SUMMARY")
        logger.info(f"{'=' * 60}")
        logger.info(f"  Total files  : {r['processed']}")
        logger.info(f"  ✅ Succeeded  : {r['success']}")
        logger.info(f"  ❌ Failed     : {r['failed']}")
        logger.info(f"  Success rate : {r['success']/max(r['processed'],1)*100:.1f}%")
        logger.info(f"{'=' * 60}\n")


def _format_customer(data: dict) -> str:
    """Quick one-liner summary of extracted customer"""
    return (
        f"name={data.get('name')}, "
        f"email={data.get('email')}, "
        f"plan={data.get('plan')}, "
        f"company={data.get('company')}"
    )
