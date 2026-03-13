import json
import logging
from openai import AsyncOpenAI

from app.config import settings, event_bus

logger = logging.getLogger("freelaas.ai")

_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=settings.DASHSCOPE_API_KEY,
            base_url=settings.QWEN_BASE_URL,
        )
    return _client


async def call_llm(
    model: str,
    system_prompt: str,
    user_message: str,
    agent_name: str = "agent",
    project_id: str = "",
) -> dict | None:
    """Call Qwen model via OpenAI-compatible API with streaming for real-time thinking visibility."""
    client = get_client()

    await event_bus.publish("agent_thinking_start", {
        "agent": agent_name,
        "project_id": project_id,
        "model": model,
        "message": f"🧠 {agent_name} analisando..."
    })

    try:
        full_response = ""
        thinking_text = ""

        stream = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.7,
            max_tokens=1024,
            stream=True,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if not delta:
                continue

            # Check for thinking/reasoning content (Qwen models with thinking)
            reasoning = getattr(delta, "reasoning_content", None)
            if reasoning:
                thinking_text += reasoning
                await event_bus.publish("agent_thinking", {
                    "agent": agent_name,
                    "project_id": project_id,
                    "chunk": reasoning,
                    "full_thinking": thinking_text,
                })

            content = delta.content
            if content:
                full_response += content
                await event_bus.publish("agent_response_chunk", {
                    "agent": agent_name,
                    "project_id": project_id,
                    "chunk": content,
                })

        await event_bus.publish("agent_thinking_end", {
            "agent": agent_name,
            "project_id": project_id,
            "thinking": thinking_text[:500] if thinking_text else "",
            "message": f"✅ {agent_name} concluiu análise"
        })

        # Parse JSON from response
        response_text = full_response.strip()
        # Handle markdown code blocks
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Try to find the first { and last }
            start = response_text.find("{")
            end = response_text.rfind("}")
            if start != -1 and end != -1:
                return json.loads(response_text[start:end+1])
            raise

    except json.JSONDecodeError as e:
        logger.error(f"{agent_name} returned invalid JSON: {e}\nResponse: {full_response[:300]}")
        await event_bus.publish("agent_error", {
            "agent": agent_name,
            "project_id": project_id,
            "message": f"❌ {agent_name}: resposta inválida do modelo"
        })
        return None
    except Exception as e:
        logger.error(f"{agent_name} failed: {e}")
        await event_bus.publish("agent_error", {
            "agent": agent_name,
            "project_id": project_id,
            "message": f"❌ {agent_name}: erro - {str(e)[:100]}"
        })
        return None
