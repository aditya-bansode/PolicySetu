"""
PolicySetu — PolicyCategory Model
=================================
Lookup table for multilingual policy domains (EN, MR, HI).
"""

from app.extensions import db


class PolicyCategory(db.Model):
    __tablename__ = "policy_categories"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name_en = db.Column(db.String(100), nullable=False, unique=True, index=True)
    name_mr = db.Column(db.String(100), nullable=True)
    name_hi = db.Column(db.String(100), nullable=True)

    def to_dict(self, lang: str = "en") -> dict:
        name = self.name_en
        if lang == "hi" and self.name_hi:
            name = self.name_hi
        elif lang == "mr" and self.name_mr:
            name = self.name_mr

        return {
            "id": self.id,
            "name": name,
            "name_en": self.name_en,
            "name_mr": self.name_mr,
            "name_hi": self.name_hi,
            "slug": self.name_en.lower().replace(" & ", "-").replace(" ", "-"),
        }
