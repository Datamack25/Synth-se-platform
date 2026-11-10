"""SYNTHEA - adaptateur optionnel vers un modele de langue.

La plateforme fonctionne entierement sans cette brique (synthese extractive,
traduction par glossaire, dialogue par recherche vectorielle). Si une cle
ANTHROPIC_API_KEY est presente dans les secrets Streamlit ou l environnement,
SCRIBE, BABEL et ECHO peuvent en plus reformuler de maniere abstractive.

Aucun appel reseau n est effectue tant que la cle est absente.
"""
from __future__ import annotations

import os

MODEL = os.environ.get("SYNTHEA_LLM_MODEL", "claude-sonnet-4-5")
_MAX = 4000


def _api_key() -> str | None:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key
    try:
        import streamlit as st
        return st.secrets.get("ANTHROPIC_API_KEY")        # type: ignore[attr-defined]
    except Exception:
        return None


def available() -> bool:
    try:
        import anthropic  # noqa: F401
    except Exception:
        return False
    return bool(_api_key())


def status() -> dict:
    try:
        import anthropic  # noqa: F401
        mod = True
    except Exception:
        mod = False
    return {
        "module_anthropic": mod,
        "cle_presente": bool(_api_key()),
        "actif": mod and bool(_api_key()),
        "modele": MODEL,
    }


def complete(prompt: str, system: str = "", max_tokens: int = 1200,
             temperature: float = 0.2) -> str:
    """Appel unique. Retourne une chaine vide en cas d indisponibilite."""
    if not available():
        return ""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=_api_key())
        msg = client.messages.create(
            model=MODEL,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system or "Tu es un analyste documentaire rigoureux. "
                             "Tu n ajoutes jamais d information absente du texte fourni.",
            messages=[{"role": "user", "content": prompt[: _MAX * 8]}],
        )
        return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    except Exception as exc:
        return f"[llm indisponible : {exc.__class__.__name__}]"


# ---------------------------------------------------------------- usages
def polish_summary(tree, lang: str = "fr") -> dict:
    """Reformule le resume executif sans ajouter de contenu."""
    src = "\n".join(f"- {c.text} ({c.ref})" for c in tree.executive)
    if not src:
        return {"actif": False, "raison": "resume executif vide"}
    txt = complete(
        "Reformule ces constats en un paragraphe continu et sobre, "
        "sans rien ajouter et en conservant les references de page entre parentheses :\n\n"
        + src,
        max_tokens=900,
    )
    return {"actif": bool(txt) and not txt.startswith("[llm"),
            "texte": txt, "langue": lang}


def rewrite_for_context(markdown: str, context_label: str, regles: str,
                        lang_label: str = "francais") -> str:
    if not available():
        return ""
    return complete(
        f"Reecris la synthese suivante pour ce contexte : {context_label}.\n"
        f"Regles de style imperatives : {regles}\n"
        f"Langue de sortie : {lang_label}.\n"
        "Interdiction d ajouter un fait, un chiffre ou un nom absent du texte. "
        "Conserve toutes les references de page.\n\n" + markdown,
        max_tokens=2500, temperature=0.3,
    )


def translate(markdown: str, lang_label: str, glossaire: str = "") -> str:
    if not available():
        return ""
    gl = f"\nGlossaire impose (respecte-le strictement) :\n{glossaire}\n" if glossaire else ""
    return complete(
        f"Traduis le texte suivant en {lang_label}. Conserve la structure "
        f"markdown, les chiffres et les references de page a l identique.{gl}\n\n"
        + markdown,
        max_tokens=3000, temperature=0.1,
    )


def answer(question: str, passages: list[tuple[str, str]], lang_label: str = "francais") -> str:
    """passages = [(reference, texte)]."""
    if not available():
        return ""
    ctx = "\n\n".join(f"[{ref}] {txt}" for ref, txt in passages)
    return complete(
        f"Reponds a la question en t appuyant uniquement sur les extraits fournis. "
        f"Cite les references entre crochets. Si les extraits ne permettent pas de "
        f"repondre, dis-le clairement. Langue : {lang_label}.\n\n"
        f"Question : {question}\n\nExtraits :\n{ctx}",
        max_tokens=1200, temperature=0.1,
    )
