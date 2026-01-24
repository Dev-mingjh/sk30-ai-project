from __future__ import annotations

from typing import Any, Dict, Optional

from openai import OpenAI

from configs.constants import DEFAULT_LLM_MODEL
from llm.client import call_llm
from llm.prompts import (
    OVERVIEW_PROMPT,
    TECHNICAL_PROMPT,
    KISA_PROCEDURE_PROMPT,
    REFERENCE_PROMPT
)


def generate_section_overview(context: Dict[str, Any], client: OpenAI, model: str = DEFAULT_LLM_MODEL) -> Dict[str, str]:
    prompt = OVERVIEW_PROMPT_TEMPLATE.format(
        attack_label=context["label"],
        anchor_techniques=", ".join(context["anchors"]),
        mitre_evidence=context["mitre_evidence"],
        kisa_evidence=context["kisa_evidence"],
    )
    return {"section": "overview", "prompt": prompt, "text": call_llm(client, model, prompt)}


def generate_section_technical(context: Dict[str, Any], client: OpenAI, model: str = DEFAULT_LLM_MODEL) -> Dict[str, str]:
    prompt = TECHNICAL_PROMPT_TEMPLATE.format(
        attack_label=context["label"],
        anchor_techniques=", ".join(context["anchors"]),
        mitre_evidence=context["mitre_evidence"],
        kisa_evidence=context["kisa_evidence"],
    )
    return {"section": "technical", "prompt": prompt, "text": call_llm(client, model, prompt)}


def generate_section_kisa(context: Dict[str, Any], client: OpenAI, model: str = DEFAULT_LLM_MODEL) -> Dict[str, str]:
    prompt = KISA_PROCEDURE_PROMPT_TEMPLATE.format(
        attack_label=context["label"],
        anchor_techniques=", ".join(context["anchors"]),
        kisa_evidence=context["kisa_evidence"],
    )
    return {"section": "kisa", "prompt": prompt, "text": call_llm(client, model, prompt)}


def generate_section_reference(context: Dict[str, Any], client: OpenAI, model: str = DEFAULT_LLM_MODEL) -> Dict[str, str]:
    web_evidence = context.get("web_evidence")
    if web_evidence is None or str(web_evidence).strip() == "":
        return {"section": "reference", "prompt": "", "text": ""}

    prompt = REFERENCE_PROMPT.format(
        attack_label=context["label"],
        anchor_techniques=", ".join(context["anchors"]),
        web_evidence=web_evidence,
    )
    return {"section": "reference", "prompt": prompt, "text": call_llm(client, model, prompt)}
