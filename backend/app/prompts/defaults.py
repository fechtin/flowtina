"""Default global prompt and seed content-type templates."""

from __future__ import annotations

DEFAULT_GLOBAL_PROMPT = (
    "You are an expert social media content writer for the Flowtina platform. "
    "Always write clear, engaging, original content. Follow safety and brand "
    "guidelines. Never invent facts. Respect the requested language and length."
)

# Built-in content-type templates keyed by type. Used when a project has no
# custom template for the requested type.
DEFAULT_TEMPLATES: dict[str, str] = {
    "short_post": (
        "Write a short, engaging {{tone}} social media post in {{language}} about: {{topic}}.\n"
        "Source context (optional):\n{{source_content}}\n"
        "Keep it under {{max_words}} words. Emoji level: {{emoji_level}}.\n"
        "End with a call to action: {{cta}}"
    ),
    "long_post": (
        "Write a long-form {{tone}} article in {{language}} about: {{topic}}.\n"
        "Source context:\n{{source_content}}\n"
        "Target audience: {{audience}}. Maximum {{max_words}} words.\n"
        "Use clear structure with short paragraphs."
    ),
    "news": (
        "Write a concise {{language}} news summary about: {{topic}}.\n"
        "Base it strictly on this source:\n{{source_content}}\n"
        "Be factual and neutral. Maximum {{max_words}} words."
    ),
    "seo": (
        "Write an SEO-optimized {{language}} article about: {{topic}}.\n"
        "Audience: {{audience}}. Include a strong title and natural keyword usage.\n"
        "Maximum {{max_words}} words."
    ),
    "marketing": (
        "Write a persuasive {{tone}} marketing post in {{language}} for {{brand_name}} about: "
        "{{topic}}. Audience: {{audience}}. Include a compelling CTA: {{cta}}."
    ),
    "educational": (
        "Write an educational {{language}} post explaining: {{topic}}.\n"
        "Audience: {{audience}}. Be clear and beginner-friendly. Maximum {{max_words}} words."
    ),
    "question": (
        "Write an engaging {{language}} question post to spark discussion about: {{topic}}. "
        "Keep it short."
    ),
    "quote": (
        "Write an inspirational {{language}} quote-style post about: {{topic}}. Keep it under "
        "{{max_words}} words."
    ),
}

DEFAULT_HASHTAG_PROMPT = (
    "Generate between 4 and 8 relevant, lowercase hashtags in {{language}} for this content:\n"
    "{{source_content}}\n"
    "Return only the hashtags separated by spaces, each starting with #. No explanations."
)

DEFAULT_SUMMARIZE_PROMPT = (
    "Summarize the following content in {{language}} in under 1500 characters, keeping the key "
    "facts:\n\n{{source_content}}"
)
