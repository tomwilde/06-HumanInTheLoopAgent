from __future__ import annotations

import os

from openai import OpenAI

from src.config import AppConfig


def maybe_generate_live_response(config: AppConfig, user_message: str) -> str | None:
    if not config.use_live_llm:
        return None

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return None

    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
    completion = client.chat.completions.create(
        model=config.openrouter_model,
        messages=[
            {
                "role": "system",
                "content": "You are a concise customer service assistant.",
            },
            {"role": "user", "content": user_message},
        ],
        temperature=0.2,
    )
    return completion.choices[0].message.content or None

