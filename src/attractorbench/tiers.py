"""Tier definitions and DoD checklist parsing for attractorbench."""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from pathlib import Path

SPECS_DIR = Path(__file__).parent.parent.parent / "specs"


@dataclass
class DoDItem:
    """A single Definition of Done checkbox item."""

    id: str  # e.g. "t1.core_infra.1"
    section: str  # e.g. "Core Infrastructure"
    section_key: str  # e.g. "core_infra"
    text: str  # The checkbox text
    is_matrix: bool = False  # True for cross-provider parity matrix items


@dataclass
class DoDSection:
    """A section of DoD items (e.g. '8.1 Core Infrastructure')."""

    number: str  # e.g. "8.1"
    name: str  # e.g. "Core Infrastructure"
    key: str  # e.g. "core_infra"
    items: list[DoDItem] = field(default_factory=list)


@dataclass
class TierDef:
    """Definition of a benchmark tier."""

    tier: int
    name: str
    slug: str  # e.g. "tier1-unified-llm"
    spec_file: str  # filename in specs/
    dod_section_number: str  # e.g. "8" for Section 8
    agent_timeout: int  # seconds
    verifier_timeout: int  # seconds
    sections: list[DoDSection] = field(default_factory=list)

    @property
    def all_items(self) -> list[DoDItem]:
        items = []
        for s in self.sections:
            items.extend(s.items)
        return items

    @property
    def total_items(self) -> int:
        return len(self.all_items)

    @property
    def spec_path(self) -> Path:
        return SPECS_DIR / self.spec_file


def _make_key(name: str) -> str:
    """Convert a section name to a snake_case key."""
    name = re.sub(r"[^a-zA-Z0-9\s]", "", name)
    return re.sub(r"\s+", "_", name.strip().lower())


def _parse_dod_sections(spec_text: str, dod_section: str) -> list[DoDSection]:
    """Parse DoD sections from a spec's Definition of Done section."""
    sections: list[DoDSection] = []

    # Find lines starting with ### {dod_section}.N
    subsection_re = re.compile(
        rf"^### ({re.escape(dod_section)}\.\d+)\s+(.+)$", re.MULTILINE
    )
    matches = list(subsection_re.finditer(spec_text))

    for i, m in enumerate(matches):
        number = m.group(1)
        name = m.group(2).strip()
        key = _make_key(name)

        # Extract text until next subsection or end
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(spec_text)
        block = spec_text[start:end]

        items: list[DoDItem] = []

        # Parse bullet checkboxes: - [ ] text
        for line in block.splitlines():
            line = line.strip()
            checkbox_match = re.match(r"^- \[ \]\s+(.+)$", line)
            if checkbox_match:
                item_num = len(items) + 1
                items.append(
                    DoDItem(
                        id=f"{number}.{item_num}",
                        section=name,
                        section_key=key,
                        text=checkbox_match.group(1),
                        is_matrix=False,
                    )
                )

        # Parse matrix checkboxes: | text | [ ] | [ ] | ...
        table_rows = re.findall(r"^\|(.+)\|$", block, re.MULTILINE)
        for row in table_rows:
            cells = [c.strip() for c in row.split("|")]
            # Skip header and separator rows
            if not cells or all(c.startswith("-") or c == "" for c in cells):
                continue
            if cells[0] in ("Test Case", ""):
                continue
            # Count [ ] cells in this row
            test_name = cells[0].strip()
            for cell_idx, cell in enumerate(cells[1:], 1):
                if "[ ]" in cell:
                    item_num = len(items) + 1
                    items.append(
                        DoDItem(
                            id=f"{number}.m{item_num}",
                            section=name,
                            section_key=key,
                            text=f"[Matrix] {test_name}" + (
                                f" (col {cell_idx})" if cell_idx > 1 or len(cells) > 2 else ""
                            ),
                            is_matrix=True,
                        )
                    )

        section = DoDSection(number=number, name=name, key=key, items=items)
        sections.append(section)

    return sections


def _load_tier(tier_def: TierDef) -> TierDef:
    """Load and parse DoD sections for a tier definition."""
    spec_path = tier_def.spec_path
    if not spec_path.exists():
        raise FileNotFoundError(f"Spec file not found: {spec_path}")
    spec_text = spec_path.read_text(encoding="utf-8")
    tier_def.sections = _parse_dod_sections(spec_text, tier_def.dod_section_number)
    # Re-ID items with tier prefix
    for section in tier_def.sections:
        for item in section.items:
            item.id = f"t{tier_def.tier}.{item.id}"
    return tier_def


TIER_DEFS: list[TierDef] = [
    TierDef(
        tier=0,
        name="Smoke Test",
        slug="tier0-smoke-test",
        spec_file="smoke-test-spec.md",
        dod_section_number="0",
        agent_timeout=300,
        verifier_timeout=120,
    ),
    TierDef(
        tier=1,
        name="Unified LLM SDK",
        slug="tier1-unified-llm",
        spec_file="unified-llm-spec.md",
        dod_section_number="8",
        agent_timeout=7200,
        verifier_timeout=600,
    ),
    TierDef(
        tier=2,
        name="Coding Agent Loop",
        slug="tier2-agent-loop",
        spec_file="coding-agent-loop-spec.md",
        dod_section_number="9",
        agent_timeout=7200,
        verifier_timeout=600,
    ),
    TierDef(
        tier=3,
        name="Attractor Pipeline",
        slug="tier3-attractor",
        spec_file="attractor-spec.md",
        dod_section_number="11",
        agent_timeout=7200,
        verifier_timeout=600,
    ),
]


MAIN_SLUG = "main"
MAIN_AGENT_TIMEOUT = 14400  # 4 hours
MAIN_VERIFIER_TIMEOUT = 900  # 15 minutes

# Backwards compatibility
FULLSTACK_SLUG = MAIN_SLUG


@dataclass
class MainTierDef:
    """Combined task definition for tiers 1-3 in a single workspace."""

    name: str  # "Main"
    slug: str  # "main"
    tiers: list[TierDef]  # [tier1, tier2, tier3], ordered
    agent_timeout: int  # 14400
    verifier_timeout: int  # 900


# Backwards compatibility
FullStackTierDef = MainTierDef


def load_main_tier() -> MainTierDef:
    """Load tiers 1, 2, 3 and bundle them into a single main task."""
    tiers = load_tiers([1, 2, 3])
    return MainTierDef(
        name="Main",
        slug=MAIN_SLUG,
        tiers=tiers,
        agent_timeout=MAIN_AGENT_TIMEOUT,
        verifier_timeout=MAIN_VERIFIER_TIMEOUT,
    )


# Backwards compatibility
load_fullstack_tier = load_main_tier


def load_tiers(tier_numbers: list[int] | None = None) -> list[TierDef]:
    """Load tier definitions, optionally filtering by tier number."""
    tier_map = {tier.tier: tier for tier in TIER_DEFS}

    if tier_numbers is None:
        tiers = TIER_DEFS
    else:
        tiers = []
        seen: set[int] = set()
        unknown = [tier for tier in tier_numbers if tier not in tier_map]
        if unknown:
            known = ", ".join(str(num) for num in sorted(tier_map))
            unknown_str = ", ".join(str(num) for num in sorted(set(unknown)))
            raise ValueError(f"Unknown tier(s): {unknown_str}. Available tiers: {known}")

        for tier_number in tier_numbers:
            if tier_number in seen:
                continue
            tiers.append(tier_map[tier_number])
            seen.add(tier_number)

    return [_load_tier(replace(tier, sections=[])) for tier in tiers]
