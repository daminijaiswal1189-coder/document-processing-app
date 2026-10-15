from __future__ import annotations

import re

import fitz
import yaml

from config.settings import CONFIG_DIR
from models.plan_profile import PlanProfile
from services.file_order import load_section_specs
from services.plan_config import bookmark_overrides, is_457_plan, package_flags

_ADP_FILE = re.compile(r"\badp\s*test\b")
_ACP_FILE = re.compile(r"\bacp\s*test\b")
_BOTH_FILE = re.compile(r"\badp\s*acp\b|\badpacp\b")
_ADP_HEADING = re.compile(r"(?im)^\s*ADP\s+Tests?\s*$")
_ACP_HEADING = re.compile(r"(?im)^\s*ACP\s+Tests?\s*$")
_BOTH_HEADING = re.compile(r"(?im)^\s*ADP\s*/\s*ACP\s+Tests?\s*$")
_TEST_HEADING = re.compile(r"(?im)^\s*(?:ADP\s*/\s*ACP|ADP|ACP)\s+Tests?\s*$")
_WRAPPER_PAGE = re.compile(
    r"cover letter|as you requested|we are pleased to provide|"
    r"result summary|test summary|summary of results|summary of compliance|"
    r"immediate action required|no immediate action is required|"
    r"failed compliance testing|excess return notice|sample/draft communication",
    re.I,
)

# Pages an ADP/ACP-only or ACP-only package is allowed to contain.
_ONLY_SECTIONS = {
    "Cover Letter",
    "Test Summary",
    "Action Required",
    "HCE/Key",
    "Future HCE",
    "ADP/ACP",
    "Failed Test Notice",
    "ADP/ACP Excess After 12 Months Current",
    "ADP/ACP Excess After 12 Months Prior",
    "ADP/ACP Excess Current Year",
    "ADP/ACP Failure Letter",
}
_ONLY_BOOKMARKS = {"Cover Letter", "Test Summary", "HCE/Key", "Future HCE", "ADP/ACP"}


def add_bookmarks(
    doc: fitz.Document,
    profile: PlanProfile,
    source_files: list[str] | None = None,
) -> int:
    """Write SOP §O bookmarks for detected sections (TEST23.docx)."""
    titles = _bookmark_map()
    overrides = bookmark_overrides(profile.plan_type)
    keep_brf = bool(package_flags(profile.plan_type).get("keep_brf"))
    testing_only = (
        is_testing_only(doc) and not profile.midyear and not is_457_plan(profile.plan_type)
    )
    toc: list[list] = []
    seen: set[str] = set()
    for section in profile.detected_sections:
        if testing_only and section.name not in _ONLY_BOOKMARKS:
            continue
        if section.name == "BRF" and not keep_brf:
            continue
        title = overrides.get(section.name) or titles.get(section.name)
        if not title:
            continue
        if section.name == "ADP/ACP" and section.name not in overrides:
            title = adp_acp_bookmark_title(profile, doc, source_files)
        if title in seen:
            continue
        page = _bookmark_page(doc, section.name, section.page)
        toc.append([1, title, page])
        seen.add(title)
    if toc:
        doc.set_toc(toc)
    return len(toc)


def is_testing_only(doc: fitz.Document) -> bool:
    """True when the package has no allocation, variance, or other test reports.

    A line on the Test Summary does not count. Another report page means the
    full valuation package, and the full bookmark list is used.
    """
    specs = [
        spec
        for spec in load_section_specs()
        if str(spec.get("name") or "") not in _ONLY_SECTIONS
    ]
    for page in doc:
        text = page.get_text("text") or ""
        if not text.strip() or _WRAPPER_PAGE.search(text):
            continue
        for spec in specs:
            aliases = [str(spec.get("name") or "")] + [str(alias) for alias in (spec.get("aliases") or [])]
            for alias in aliases:
                if len(alias) < 3:
                    continue
                if re.search(re.escape(alias), text, re.I):
                    return False
    return True


def _bookmark_page(doc: fitz.Document, section_name: str, detected_page: int) -> int:
    """The cover sentence 'ADP/ACP test is included' is not the test bookmark."""
    if section_name == "ADP/ACP":
        for index, page in enumerate(doc):
            if _TEST_HEADING.search(page.get_text("text") or ""):
                return index + 1
    if doc.page_count == 0:
        return 1
    return max(1, min(detected_page, doc.page_count))


def adp_acp_bookmark_title(
    profile: PlanProfile,
    doc: fitz.Document | None = None,
    source_files: list[str] | None = None,
) -> str:
    """TEST23 §O: ADP Test, ACP Test, or ADP/ACP Tests from what is in the package."""
    override = bookmark_overrides(profile.plan_type).get("ADP/ACP")
    if override:
        return override
    has_adp, has_acp = _adp_acp_present(source_files or [], doc)
    if has_adp and not has_acp:
        return "ADP Test"
    if has_acp and not has_adp:
        return "ACP Test"
    return "ADP/ACP Tests"


def _adp_acp_present(source_files: list[str], doc: fitz.Document | None) -> tuple[bool, bool]:
    blob = " ".join(_file_tokens(name) for name in source_files)
    has_adp = bool(_ADP_FILE.search(blob) or _BOTH_FILE.search(blob))
    has_acp = bool(_ACP_FILE.search(blob) or _BOTH_FILE.search(blob))
    if doc is not None:
        page_text = "\n".join((page.get_text("text") or "") for page in doc)
        if _BOTH_HEADING.search(page_text):
            has_adp = True
            has_acp = True
        if _ADP_HEADING.search(page_text):
            has_adp = True
        if _ACP_HEADING.search(page_text):
            has_acp = True
    return has_adp, has_acp


def _file_tokens(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", name.lower())


def _bookmark_map() -> dict[str, str]:
    data = yaml.safe_load((CONFIG_DIR / "sections.yaml").read_text(encoding="utf-8")) or {}
    raw = data.get("bookmarks") or {}
    if isinstance(raw, dict):
        return {str(key): str(value) for key, value in raw.items()}
    return {str(item): str(item) for item in raw}
