"""
test_response_agent.py — Test Response Agent Draft Generation
Run this to verify AG-04 generates responses based on subject and body.
"""
import asyncio
import json
import logging
from agents.response_agent import response_node
from state.shared_state import AgentState

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_response_generation():
    """Test response agent with a sample email"""
    
    # Sample email state
    test_state: AgentState = {
        "email_id": "test-123",
        "case_reference": "CASE-20260319-abc123",
        "parsed_email": {
            "email_id": "test-123",
            "sender": "customer@example.com",
            "subject": "Password reset request",
            "body": "Hi, I forgot my password and cannot log in. Please help me reset it.",
            "thread_id": "thread-123",
            "source": "gmail"
        },
        "email_text": "Hi, I forgot my password and cannot log in. Please help me reset it.",
        "email_subject": "Password reset request",
        "classification_result": {
            "category": "password_reset",
            "priority": "medium",
            "confidence": 0.95,
            "sentiment_score": 0.1
        },
        "confidence": 0.95,
        "sentiment_score": 0.1,
        "pii_scan_result": {"is_safe": True, "detected_types": []},
        "domain_config": {
            "domain_id": "it_support",
            "display_name": "IT Support",
            "response_tone": "technical, concise, solution-focused",
            "compliance": {
                "auto_send_allowed": True,
                "standards": ["ISO27001"]
            },
            "auto_send_types": ["password_reset", "general_query"]
        },
        "agent_statuses": {},
        "event_queue": [],
        "current_step": "response",
        "customer_context": {},
        "email_thread": []
    }
    
    logger.info("=" * 80)
    logger.info("Testing Response Agent Draft Generation")
    logger.info("=" * 80)
    logger.info(f"Email Subject: {test_state['email_subject']}")
    logger.info(f"Email Body: {test_state['email_text']}")
    logger.info(f"Category: {test_state['classification_result']['category']}")
    logger.info(f"Confidence: {test_state['confidence']}")
    logger.info("=" * 80)
    
    # Call response agent
    result = await response_node(test_state)
    
    logger.info("=" * 80)
    logger.info("RESPONSE AGENT RESULT:")
    logger.info("=" * 80)
    logger.info(f"Draft Generated: {result.get('draft') is not None}")
    logger.info(f"Agent Status: {result.get('agent_statuses', {}).get('AG-04')}")
    logger.info(f"Current Step: {result.get('current_step')}")
    logger.info(f"PII Safe: {result.get('pii_scan_result', {}).get('is_safe')}")
    
    if result.get('draft'):
        logger.info("=" * 80)
        logger.info("GENERATED DRAFT:")
        logger.info("=" * 80)
        logger.info(result['draft'])
        logger.info("=" * 80)
    else:
        logger.warning("No draft was generated!")
    
    return result

if __name__ == "__main__":
    print("\n🚀 Testing Response Agent...\n")
    result = asyncio.run(test_response_generation())
    
    if result.get('draft'):
        print("\n✅ SUCCESS: Response Agent generated a draft!")
        print(f"\n📧 Draft Preview:\n{result['draft'][:200]}...")
    else:
        print("\n❌ FAILED: No draft generated")
        print(f"Reason: {result.get('agent_statuses', {}).get('AG-04')}")
