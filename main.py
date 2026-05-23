"""
main.py
-------
Entry point — yahan se sab kuch start hota hai.

Run karne ka tarika:
  python main.py                        # mock mode (default)
  python main.py --provider gemini      # real Gemini LLM
  python main.py --real-s3 --real-crm  # real AWS S3 + CRM

Environment variables (.env file mein):
  GEMINI_API_KEY   = your_gemini_key
  AWS_ACCESS_KEY_ID     = your_aws_key
  AWS_SECRET_ACCESS_KEY = your_aws_secret
  CRM_BASE_URL     = https://your-crm.com/api
  CRM_API_KEY      = your_crm_api_key
  MOCK_FAIL_RATE   = 0.0  (0.0 to 1.0, for testing retry logic)
"""

import argparse
from dotenv import load_dotenv
from agents.orchestrator import OnboardingOrchestrator
from utils.logger import get_logger

# .env file se environment variables load karo
load_dotenv()

logger = get_logger("main")


def parse_args():
    parser = argparse.ArgumentParser(
        description="UnifyApps FDSE: Enterprise Customer Onboarding Agent"
    )
    parser.add_argument(
        "--provider",
        choices=["mock", "gemini", "huggingface"],
        default="mock",
        help="LLM provider for parsing (default: mock)"
    )
    parser.add_argument(
        "--bucket",
        default="enterprise-onboarding",
        help="S3 bucket name (default: enterprise-onboarding)"
    )
    parser.add_argument(
        "--real-s3",
        action="store_true",
        help="Use real AWS S3 (requires AWS credentials)"
    )
    parser.add_argument(
        "--real-crm",
        action="store_true",
        help="Use real CRM API (requires CRM_BASE_URL + CRM_API_KEY)"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Mock mode = True agar real flags nahi lagate
    mock_mode = not (args.real_s3 or args.real_crm)

    logger.info(f"🎯 Starting pipeline | LLM: {args.provider} | Mock: {mock_mode}")

    # Orchestrator banao aur run karo
    agent = OnboardingOrchestrator(
        bucket_name=args.bucket,
        llm_provider=args.provider,
        mock_mode=mock_mode,
    )

    results = agent.run()

    # Exit code: 0 = success, 1 = kuch fail hua
    if results["failed"] > 0:
        logger.warning(f"⚠️  {results['failed']} customer(s) failed. Check logs above.")
        exit(1)
    else:
        logger.info("✅ All customers processed successfully!")
        exit(0)


if __name__ == "__main__":
    main()
