"""What a "Verified from accounting data" card is allowed to sit under.

The card renders that badge next to figures the report services produced. On
the deterministic path the sentence above it is also the services' -- the
handler formats the same Decimals into both. On the model path it is not: the
figures in the card come from a DTO, the sentence comes from a model, and
nothing has ever checked that they agree.

This module is that check, and it runs BEFORE the first model-path card
exists, so no release ever shows the badge over unchecked prose.

TWO RULES

1. One kind per turn. A turn that produced groundings of more than one kind
   attaches none. Rule 2 cannot catch a trial-balance card under
   profit-and-loss prose when the two reports happen to share a figure, and
   "happen to share a figure" is ordinary in accounting -- a one-line company
   has the same number in half its reports. So the ambiguity is refused
   rather than resolved.

2. Every number in the prose is one the grounding knows. Money, and also
   codes, identifiers, counts and dates, because those appear in answers too
   and a gate that refuses "account 1110" is a gate that gets switched off.
   A number the grounding cannot account for means the model produced it, and
   the card comes off.

WHAT THIS DOES NOT CATCH, AND WILL NOT

  - A right number under a wrong label. "Revenue was 1,500.00" when 1,500.00
    is the expense total passes: the value is in the grounding, and nothing
    here reads the sentence.
  - A figure with no digits. "roughly thirty-one thousand" contains no token
    to compare.
  - A derived figure that lands on a permitted number by coincidence.

Each has a test below that asserts the gap rather than pretending it away.
The reason to keep the gate anyway is the class it does catch: a figure that
is not in the report at all, which is what an invented or mis-copied number
looks like.

The gate is not a security control. Company isolation is the company_id in
the SQL; this is about whether a badge is honest.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import BaseModel

# A number as it appears in a reply: 1500, 1,500.00, 31337.00, 0.5.
# Leading separators are not part of the token, so "-300" yields 300; sign is
# not compared, because a reply may phrase an expense either way.
_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")

# Numbers nobody needs a report to write: ordinals and small counts that
# appear in prose as language rather than as data ("the first entry", "3
# accounts"). Kept deliberately small -- every entry here is a hole.
_LANGUAGE_NUMBERS = frozenset(Decimal(value) for value in range(0, 11))


@dataclass(frozen=True, slots=True)
class GateDecision:
    """Whether a card may be attached, and why not when it may not."""

    attach: bool
    grounding: BaseModel | None
    reason: str
    unvouched: tuple[str, ...] = ()

    @property
    def verified(self) -> bool:
        """True only when a card is attached. There is no third state."""
        return self.attach and self.grounding is not None


def _decimal(token: str) -> Decimal | None:
    try:
        return Decimal(token.replace(",", ""))
    except InvalidOperation:
        return None


def numbers_in_text(text: str) -> list[str]:
    """Every numeric token in a reply, in the order it appears."""
    return _NUMBER.findall(text or "")


def _walk(value: Any) -> list[Any]:
    """Every leaf in a grounding, whatever shape it takes.

    Groundings are Pydantic models holding nested models, dicts and lists;
    the figures live at different depths in each kind. Walking the whole
    structure means a new grounding kind is covered the day it is added,
    rather than the day someone remembers to update a list of field names.
    """
    if isinstance(value, BaseModel):
        return _walk(value.model_dump())
    if isinstance(value, dict):
        return [leaf for item in value.values() for leaf in _walk(item)]
    if isinstance(value, (list, tuple, set)):
        return [leaf for item in value for leaf in _walk(item)]
    return [value]


def numbers_the_grounding_knows(grounding: BaseModel) -> set[Decimal]:
    """Every number a grounded card can account for.

    Figures, account codes, identifiers, counts and the digits of its dates:
    a reply legitimately mentions all of them, and the gate exists to catch
    the numbers that are in none of them.
    """
    known: set[Decimal] = set()
    for leaf in _walk(grounding):
        if isinstance(leaf, bool) or leaf is None:
            continue
        if isinstance(leaf, (int, float, Decimal)):
            parsed = _decimal(str(leaf))
            if parsed is not None:
                known.add(abs(parsed))
            continue
        if isinstance(leaf, str):
            for token in numbers_in_text(leaf):
                parsed = _decimal(token)
                if parsed is not None:
                    known.add(abs(parsed))
    return known


def unvouched_numbers(text: str, grounding: BaseModel) -> list[str]:
    """Numbers in the prose that the grounding cannot account for."""
    known = numbers_the_grounding_knows(grounding)
    unvouched: list[str] = []
    for token in numbers_in_text(text):
        parsed = _decimal(token)
        if parsed is None:
            continue
        value = abs(parsed)
        if value in known or value in _LANGUAGE_NUMBERS:
            continue
        # 1,500.00 and 1500 are the same figure written twice.
        if any(value == candidate for candidate in known):
            continue
        unvouched.append(token)
    return unvouched


def decide(text: str, groundings: list[BaseModel]) -> GateDecision:
    """Whether this reply may carry a verified card.

    Refusal is the default: no grounding, more than one kind, or a number the
    grounding cannot account for, and the reply goes out with no card and no
    badge. A reply without a card is an ordinary answer; a card over an
    unchecked figure is a claim the product cannot support.
    """
    if not groundings:
        return GateDecision(False, None, "no_grounding")

    kinds = {getattr(grounding, "kind", None) for grounding in groundings}
    if len(kinds) > 1:
        # Last-grounded-wins would pick one here, and the failure mode is a
        # trial-balance card under profit-and-loss prose. Rule 2 cannot see
        # that when the two reports share a figure, so the turn gets no card.
        return GateDecision(
            False, None, "several_kinds", tuple(sorted(str(kind) for kind in kinds))
        )

    # Same kind twice means the model asked the same report for two periods;
    # the last one is the one it answered from.
    grounding = groundings[-1]

    if getattr(grounding, "status", None) != "grounded":
        return GateDecision(False, None, "grounding_unavailable")

    unvouched = unvouched_numbers(text, grounding)
    if unvouched:
        return GateDecision(False, None, "unvouched_numbers", tuple(unvouched))

    return GateDecision(True, grounding, "vouched")
