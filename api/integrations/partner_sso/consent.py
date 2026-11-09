"""Versioned consent documents (spec B §3.3). Each adapter keeps its own text."""
from dataclasses import dataclass


@dataclass(frozen=True)
class ConsentSection:
    title: str
    body: str


@dataclass(frozen=True)
class ConsentDocument:
    version: str
    title: str
    subtitle: str
    purpose: str
    sections: tuple
    notes: tuple
    # Contains the tokens {terms} and {privacy}; the frontend renders them as links.
    checkbox_label: str
    terms_url: str
    privacy_url: str

    def as_dict(self):
        return {
            "version": self.version,
            "title": self.title,
            "subtitle": self.subtitle,
            "purpose": self.purpose,
            "sections": [{"title": section.title, "body": section.body} for section in self.sections],
            "notes": list(self.notes),
            "checkbox_label": self.checkbox_label,
            "terms_url": self.terms_url,
            "privacy_url": self.privacy_url,
        }
