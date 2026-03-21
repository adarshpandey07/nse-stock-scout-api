"""Claude AI probability estimation for Polymarket events."""

import asyncio
import json
import logging

import anthropic

from app.config import settings

logger = logging.getLogger(__name__)

# Rate limiter: max 5 concurrent Claude calls
_semaphore = asyncio.Semaphore(5)

ANALYST_SYSTEM_PROMPT = """You are a calibrated prediction market analyst. Your job is to estimate the TRUE probability of binary event outcomes.

Rules:
1. Output ONLY valid JSON: {"probability": float, "confidence": "low"|"medium"|"high", "reasoning": "2-3 sentences"}
2. probability must be between 0.01 and 0.99 (never 0 or 1 — nothing is certain)
3. Be well-calibrated: when you say 70%, events should happen ~70% of the time
4. If genuinely uncertain, say so and give confidence "low" — don't default to 0.50
5. Consider base rates, current evidence, and common cognitive biases
6. Account for the resolution date — closer dates have more predictable outcomes
7. If the market price seems correct, your probability should be close to it — only deviate with strong reasoning"""


async def estimate_probability(
    question: str,
    description: str = "",
    market_price: float = 0.5,
    news_context: list[str] | None = None,
    end_date: str | None = None,
) -> dict:
    """Call Claude Opus to estimate true probability for a market event.

    Returns: {probability: float, confidence: str, reasoning: str}
    """
    if not settings.anthropic_api_key:
        return {"probability": market_price, "confidence": "low",
                "reasoning": "No Anthropic API key configured — returning market price as default"}

    news_text = ""
    if news_context:
        news_text = "\n\nRelevant recent news:\n" + "\n".join(f"- {n}" for n in news_context[:10])

    user_prompt = f"""Estimate the probability of YES for this prediction market:

Question: {question}
Description: {description}
Current market price (YES): ${market_price:.2f} (implied {market_price*100:.0f}% probability)
Resolution date: {end_date or 'Unknown'}
{news_text}

Respond with JSON only."""

    async with _semaphore:
        try:
            client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
            response = await client.messages.create(
                model=settings.anthropic_model,
                max_tokens=300,
                system=ANALYST_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )

            text = response.content[0].text.strip()
            # Extract JSON from response (handle markdown code blocks)
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()

            result = json.loads(text)

            # Validate
            prob = float(result.get("probability", market_price))
            prob = max(0.01, min(0.99, prob))
            confidence = result.get("confidence", "medium")
            if confidence not in ("low", "medium", "high"):
                confidence = "medium"
            reasoning = result.get("reasoning", "")

            return {
                "probability": round(prob, 4),
                "confidence": confidence,
                "reasoning": reasoning[:500],
            }

        except json.JSONDecodeError as e:
            logger.error(f"Claude response not valid JSON: {e}")
            return {"probability": market_price, "confidence": "low",
                    "reasoning": f"Failed to parse Claude response: {e}"}
        except Exception as e:
            logger.error(f"Claude API call failed: {e}")
            return {"probability": market_price, "confidence": "low",
                    "reasoning": f"Claude API error: {e}"}


async def analyze_news_impact(
    question: str,
    news_headline: str,
    news_body: str = "",
    current_price: float = 0.5,
) -> dict:
    """For Strategy 3: Given breaking news, estimate price impact.

    Returns: {direction: 'up'|'down'|'neutral', magnitude: float, speed: 'fast'|'slow', reasoning: str}
    """
    if not settings.anthropic_api_key:
        return {"direction": "neutral", "magnitude": 0, "speed": "slow",
                "reasoning": "No API key"}

    user_prompt = f"""A prediction market asks: "{question}"
Current YES price: ${current_price:.2f}

Breaking news just dropped:
Headline: {news_headline}
{f'Body: {news_body[:500]}' if news_body else ''}

How will this news impact the market price? Respond with JSON only:
{{"direction": "up"|"down"|"neutral", "magnitude": float (0-0.5, how much price will move), "speed": "fast"|"slow", "reasoning": "1-2 sentences"}}"""

    async with _semaphore:
        try:
            client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
            response = await client.messages.create(
                model=settings.anthropic_model,
                max_tokens=200,
                system="You are a prediction market analyst. Estimate news impact on market prices. Output ONLY valid JSON.",
                messages=[{"role": "user", "content": user_prompt}],
            )

            text = response.content[0].text.strip()
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()

            result = json.loads(text)
            return {
                "direction": result.get("direction", "neutral"),
                "magnitude": min(float(result.get("magnitude", 0)), 0.5),
                "speed": result.get("speed", "slow"),
                "reasoning": result.get("reasoning", "")[:300],
            }

        except Exception as e:
            logger.error(f"News impact analysis failed: {e}")
            return {"direction": "neutral", "magnitude": 0, "speed": "slow",
                    "reasoning": f"Analysis error: {e}"}


async def batch_analyze_markets(
    markets: list[dict],
    max_concurrent: int = 5,
) -> list[dict]:
    """Analyze multiple markets in parallel.

    Each market dict should have: question, description, yes_price, end_date
    Returns list of {condition_id, probability, confidence, reasoning, edge}
    """
    results = []

    async def analyze_one(market: dict) -> dict:
        yes_price = float(market.get("yes_price", 0.5))
        est = await estimate_probability(
            question=market.get("question", ""),
            description=market.get("description", ""),
            market_price=yes_price,
            end_date=market.get("end_date"),
        )
        edge = round(est["probability"] - yes_price, 4)
        return {
            "condition_id": market.get("condition_id", ""),
            "question": market.get("question", ""),
            "market_price": yes_price,
            **est,
            "edge": edge,
            "abs_edge": abs(edge),
        }

    # Run in batches to respect semaphore
    tasks = [analyze_one(m) for m in markets]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter out exceptions
    return [r for r in results if isinstance(r, dict)]
