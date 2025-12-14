from sqlalchemy.orm import Session
from app.models.prompt_template import PromptTemplate


DEFAULT_TEMPLATES = [
    {
        "key": "system.assist.v1",
        "role": "system",
        "version": 1,
        "template": "You are TopFuelAuto Assist. Provide advisory insights only; never handle payments or bids. Keep responses concise and structured.",
        "schema_json": {"type": "object", "properties": {"notes": {"type": "string"}}},
    },
    {
        "key": "market.scout.v1",
        "role": "agent",
        "version": 1,
        "template": "Scout relevant listings and summarize risk/price signals. Output JSON summary.",
        "schema_json": {"type": "object", "properties": {"summary": {"type": "string"}}},
    },
    {
        "key": "risk.flags.v1",
        "role": "agent",
        "version": 1,
        "template": "Identify potential risks. Output JSON array of flags with severity.",
        "schema_json": {"type": "array"},
    },
    {
        "key": "score.rank.v1",
        "role": "agent",
        "version": 1,
        "template": "Rank options and assign scores 0-100.",
        "schema_json": {"type": "object", "properties": {"scores": {"type": "array"}}},
    },
    {
        "key": "report.write.v1",
        "role": "agent",
        "version": 1,
        "template": "Write a concise markdown report combining findings and recommendations.",
        "schema_json": {"type": "object", "properties": {"report_md": {"type": "string"}}},
    },
]


def ensure_default_templates(db: Session):
    for tpl in DEFAULT_TEMPLATES:
        existing = db.query(PromptTemplate).filter(PromptTemplate.key == tpl["key"]).first()
        if existing:
            continue
        db.add(PromptTemplate(**tpl))
    db.commit()


def get_active_template(db: Session, key: str) -> PromptTemplate | None:
    return db.query(PromptTemplate).filter(PromptTemplate.key == key, PromptTemplate.is_active.is_(True)).first()
