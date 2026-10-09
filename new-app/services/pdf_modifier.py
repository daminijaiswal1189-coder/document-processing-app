from __future__ import annotations

import re

import fitz
import yaml

from config.settings import CONFIG_DIR
from models.plan_profile import PlanProfile
from models.review import RuleDecision
from services.change_marks import add_mark
from services.package_polish import hce_max_percent

_TITLE_ONLY = re.compile(
    r"^(action required|annual valuation report(?:/action required)?)\s*$",
    re.I,
)


def apply_decisions(doc: fitz.Document, decisions: list[RuleDecision]) -> list[str]:
    """Remove Action Required blocks, pack leftover text, and drop empty pages."""
    specs = _block_specs()
    remove_ids = {item.rule_id for item in decisions if item.action == "remove"}
    headings = [str(spec["heading"]) for spec in specs if spec.get("heading")]
    removed: list[str] = []
    touched: set[int] = set()
    for page in doc:
        boxes: list[fitz.Rect] = []
        for spec in specs:
            rule_id = str(spec["id"])
            heading = str(spec.get("heading") or "")
            if rule_id not in remove_ids or not heading:
                continue
            page_text = page.get_text("text") or ""
            extra = str(spec.get("extra") or "")
            if not _extra_matches(page_text, extra):
                continue
            for hit in page.search_for(heading):
                if _covered_by_longer_heading(page, hit, heading, headings):
                    continue
                end_y = _block_end(page, hit.y0, headings)
                if not _block_matches(page, spec, hit.y0, end_y):
                    continue
                if _kept_by_other_spec(page, page_text, specs, heading, hit.y0, end_y, remove_ids):
                    continue
                boxes.append(fitz.Rect(40, max(36, hit.y0 - 2), page.rect.x1 - 40, end_y))
                if rule_id not in removed:
                    removed.append(rule_id)
        for box in boxes:
            page.add_redact_annot(box, fill=(1, 1, 1), text="")
        if boxes:
            page.apply_redactions()
            touched.add(page.number)
    if touched:
        _restack_pages(doc, touched)
        _drop_empty_pages(doc)
    return removed


def _extra_matches(page_text: str, extra: str) -> bool:
    """'For current-method testing' also matches the notice line 'Current method testing:'."""
    if not extra:
        return True
    def fold(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
    haystack = fold(page_text)
    needle = fold(extra)
    if needle in haystack:
        return True
    if needle.startswith("for "):
        return needle[4:] in haystack
    return False


def _covered_by_longer_heading(page: fitz.Page, hit, heading: str, headings: list[str]) -> bool:
    """'Failed Compliance Testing' is the start of the after-12-month heading."""
    for other in headings:
        if not other.startswith(heading) or len(other) <= len(heading):
            continue
        for rect in page.search_for(other):
            if abs(rect.y0 - hit.y0) <= 2 and abs(rect.x0 - hit.x0) <= 2:
                return True
    return False


def _block_end(page: fitz.Page, y0: float, headings: list[str]) -> float:
    """Stop at the next heading, including another copy of this same heading."""
    end_y = page.rect.y1 - 36
    seen: set[str] = set()
    for heading in headings:
        if not heading or heading in seen:
            continue
        seen.add(heading)
        for rect in page.search_for(heading):
            if rect.y0 > y0 + 8:
                end_y = min(end_y, rect.y0 - 4)
    return end_y


def _kept_by_other_spec(
    page: fitz.Page,
    page_text: str,
    specs: list[dict],
    heading: str,
    y0: float,
    y1: float,
    remove_ids: set[str],
) -> bool:
    """A combined ADP/ACP letter stays when either test still needs it."""
    for spec in specs:
        if str(spec.get("heading") or "") != heading:
            continue
        if str(spec["id"]) in remove_ids:
            continue
        if not _extra_matches(page_text, str(spec.get("extra") or "")):
            continue
        if _block_matches(page, spec, y0, y1):
            return True
    return False


def _block_matches(page: fitz.Page, spec: dict, y0: float, y1: float) -> bool:
    """Prior and Current share one heading. The Current block says 'unless QNEC'."""
    contains = str(spec.get("block_contains") or "").lower()
    excludes = str(spec.get("block_excludes") or "").lower()
    if not contains and not excludes:
        return True
    words = page.get_text("words") or []
    text = " ".join(
        word[4] for word in words if word[1] >= y0 - 1 and word[3] <= y1 + 1
    ).lower()
    if contains and contains not in text:
        return False
    if excludes and excludes in text:
        return False
    return True


def _restack_pages(doc: fitz.Document, touched: set[int]) -> None:
    """Shift leftover text up, keeping font/size/color. Images stay put."""
    for page in doc:
        if page.number not in touched:
            continue
        blocks = _text_blocks(page)
        if not blocks:
            continue
        header_bottom, footer_top = _image_bands(page)
        for block in blocks:
            page.add_redact_annot(block["bbox"] + (-1, -1, 1, 1), fill=(1, 1, 1), text="")
        page.apply_redactions()
        cursor = header_bottom
        for block in blocks:
            height = block["bbox"].height
            if cursor + height > footer_top:
                break
            delta = cursor - block["bbox"].y0
            for span in block["spans"]:
                _write_span(page, span, delta)
            cursor += height + 8


def _text_blocks(page: fitz.Page) -> list[dict]:
    blocks: list[dict] = []
    for raw in page.get_text("dict").get("blocks") or []:
        if raw.get("type") != 0:
            continue
        spans: list[dict] = []
        for line in raw.get("lines") or []:
            for span in line.get("spans") or []:
                text = span.get("text") or ""
                if not text.strip():
                    continue
                origin = span.get("origin") or (span["bbox"][0], span["bbox"][3])
                spans.append(
                    {
                        "text": text,
                        "origin": fitz.Point(origin[0], origin[1]),
                        "size": float(span.get("size") or 11),
                        "font": str(span.get("font") or ""),
                        "flags": int(span.get("flags") or 0),
                        "color": span.get("color") or 0,
                    }
                )
        if not spans:
            continue
        blocks.append({"bbox": fitz.Rect(raw["bbox"]), "spans": spans})
    blocks.sort(key=lambda item: (round(item["bbox"].y0, 1), item["bbox"].x0))
    return blocks


def _image_bands(page: fitz.Page) -> tuple[float, float]:
    header = 54.0
    footer = page.rect.y1 - 36.0
    mid = page.rect.y0 + page.rect.height * 0.4
    low = page.rect.y0 + page.rect.height * 0.7
    for raw in page.get_text("dict").get("blocks") or []:
        if raw.get("type") != 1:
            continue
        rect = fitz.Rect(raw["bbox"])
        if rect.y1 <= mid:
            header = max(header, rect.y1 + 8)
        if rect.y0 >= low:
            footer = min(footer, rect.y0 - 8)
    return header, footer


def _write_span(page: fitz.Page, span: dict, delta: float) -> None:
    point = fitz.Point(span["origin"].x, span["origin"].y + delta)
    fontname = _base_font(span["font"], span["flags"])
    try:
        page.insert_text(
            point,
            span["text"],
            fontsize=span["size"],
            fontname=fontname,
            color=_rgb(span["color"]),
            overlay=True,
        )
    except Exception:
        page.insert_text(
            point,
            span["text"],
            fontsize=span["size"],
            fontname="helv",
            color=_rgb(span["color"]),
            overlay=True,
        )


def _base_font(font: str, flags: int) -> str:
    name = (font or "").lower()
    bold = bool(flags & 16) or "bold" in name
    italic = bool(flags & 2) or "italic" in name or "oblique" in name
    serif = any(token in name for token in ("times", "roman", "georgia", "cambria", "garamond", "palatino"))
    mono = any(token in name for token in ("courier", "mono", "consolas"))
    if mono:
        return { (True, True): "cobi", (True, False): "cobo", (False, True): "coit" }.get((bold, italic), "cour")
    if serif:
        return { (True, True): "tibi", (True, False): "tibo", (False, True): "titi" }.get((bold, italic), "tiro")
    return { (True, True): "hibi", (True, False): "hebo", (False, True): "heit" }.get((bold, italic), "helv")


def _rgb(color: object) -> tuple[float, float, float]:
    if isinstance(color, (tuple, list)) and len(color) >= 3:
        values = [float(item) for item in color[:3]]
        if max(values) > 1:
            return values[0] / 255, values[1] / 255, values[2] / 255
        return values[0], values[1], values[2]
    value = int(color or 0)
    return ((value >> 16) & 255) / 255, ((value >> 8) & 255) / 255, (value & 255) / 255


def _drop_empty_pages(doc: fitz.Document) -> None:
    drop: list[int] = []
    for page in doc:
        if page.number == 0:
            continue
        if page.get_images():
            continue
        if _is_empty_text(page.get_text("text") or ""):
            drop.append(page.number)
    for number in reversed(drop):
        if doc.page_count <= 1:
            break
        doc.delete_page(number)


def _is_empty_text(text: str) -> bool:
    cleaned = re.sub(r"\s+", " ", text).strip()
    return not cleaned or bool(_TITLE_ONLY.match(cleaned))


def fill_qnec_placeholders(
    doc: fitz.Document,
    profile: PlanProfile,
    marks: list[dict] | None = None,
) -> list[str]:
    """TEST23 §C: write QNEC amounts onto the CURRENT Excess Return Notice."""
    filled: list[str] = []
    total = profile.total_qnec
    for page in doc:
        original = page.get_text("text") or ""
        if "$X,XXX,XXX.XX" not in original:
            continue
        placed: list[str] = []
        updated = re.sub(r"\s+", " ", original)
        if total is not None:
            money = _money(total)
            updated = updated.replace(
                "The amount of the QNEC that is required to pass the ADP/ACP test is $X,XXX,XXX.XX",
                f"The amount of the QNEC that is required to pass the ADP/ACP test is {money}",
            )
            updated = updated.replace("ADP/ACP test is $X,XXX,XXX.XX", f"ADP/ACP test is {money}")
            filled.append(f"total={money}")
            placed.append(money)
        if profile.adp_qnec is not None:
            updated = updated.replace(
                "The ADP QNEC is $X,XXX,XXX.XX",
                f"The ADP QNEC is {_money(profile.adp_qnec)}",
            )
            filled.append(f"adp={_money(profile.adp_qnec)}")
            placed.append(_money(profile.adp_qnec))
        else:
            updated = re.sub(r"The ADP QNEC is \$X,XXX,XXX\.XX\.?\n?", "", updated)
        if profile.acp_qnec is not None:
            updated = updated.replace(
                "The ACP QNEC is $X,XXX,XXX.XX",
                f"The ACP QNEC is {_money(profile.acp_qnec)}",
            )
            filled.append(f"acp={_money(profile.acp_qnec)}")
            placed.append(_money(profile.acp_qnec))
        else:
            updated = re.sub(r"The ACP QNEC is \$X,XXX,XXX\.XX\.?\n?", "", updated)
        if profile.deferral_refund is not None:
            updated = updated.replace(
                "Deferral Contribution of $X,XXX,XXX.XX",
                f"Deferral Contribution of {_money(profile.deferral_refund)}",
            )
            filled.append(f"deferral={_money(profile.deferral_refund)}")
            placed.append(_money(profile.deferral_refund))
        else:
            updated = re.sub(r"Deferral Contribution of \$X,XXX,XXX\.XX\.?\s*", "", updated)
        if profile.match_refund is not None:
            updated = updated.replace(
                "Match Contribution of $X,XXX,XXX.XX",
                f"Match Contribution of {_money(profile.match_refund)}",
            )
            filled.append(f"match={_money(profile.match_refund)}")
            placed.append(_money(profile.match_refund))
        else:
            updated = re.sub(r"Match Contribution of \$X,XXX,XXX\.XX\.?\s*", "", updated)
        if updated != original:
            page.add_redact_annot(page.rect, fill=(1, 1, 1), text="")
            page.apply_redactions()
            page.insert_textbox(fitz.Rect(54, 54, 558, 738), updated, fontsize=11, fontname="helv")
            seen: set[str] = set()
            for phrase in placed:
                if phrase in seen:
                    continue
                seen.add(phrase)
                for hit in page.search_for(phrase):
                    add_mark(marks, page.number, hit, "Filled amount")
    return filled


def _money(value: float) -> str:
    return f"${value:,.2f}"


def _block_specs() -> list[dict]:
    data = yaml.safe_load((CONFIG_DIR / "paragraphs.yaml").read_text(encoding="utf-8")) or {}
    specs = list(data.get("action_required_headings") or [])
    specs.extend(data.get("notices") or [])
    specs.extend(data.get("sample_letters") or [])
    specs.extend(data.get("excess_summary") or [])
    specs.sort(key=lambda item: -len(str(item.get("heading") or "")))
    return specs


_ADP_NHCE = re.compile(
    r"ADP\s+for\s+the\s+\d+\s+NHCE\(?s\)?\s+is\s+(\d+(?:\.\d+)?)\s*%",
    re.I,
)


def apply_recap_bullets(doc: fitz.Document, decisions: list[RuleDecision]) -> list[str]:
    """TEST23 §I: drop unused Important Information bullets and pack the page."""
    specs = _recap_specs()
    if not specs:
        return []
    remove_ids = {item.rule_id for item in decisions if item.action == "remove"}
    nhce = _adp_nhce_percent(doc)
    removed: list[str] = []
    for page in doc:
        original = page.get_text("text") or ""
        if "important information" not in original.lower():
            continue
        header, bullets = _split_recap(original)
        kept: list[str] = []
        for bullet in bullets:
            spec = _matching_recap(bullet, specs)
            if spec and str(spec["id"]) in remove_ids:
                if spec["id"] not in removed:
                    removed.append(str(spec["id"]))
                continue
            if spec and str(spec["id"]) == "Y2":
                bullet = _fill_prior_rates(bullet, nhce)
            kept.append(bullet)
        updated = header.strip()
        if kept:
            updated = updated + "\n\n" + "\n\n".join(f"- {item}" for item in kept)
        if updated.strip() == original.strip():
            continue
        page.add_redact_annot(page.rect, fill=(1, 1, 1), text="")
        page.apply_redactions()
        page.insert_textbox(fitz.Rect(54, 54, 558, 738), updated.strip(), fontsize=11, fontname="helv")
    return removed


def _recap_specs() -> list[dict]:
    data = yaml.safe_load((CONFIG_DIR / "paragraphs.yaml").read_text(encoding="utf-8")) or {}
    return list(data.get("recap_bullets") or [])


def _matching_recap(bullet: str, specs: list[dict]) -> dict | None:
    text = bullet.lower()
    hits = [
        spec
        for spec in specs
        if (match := str(spec.get("match") or "").lower()) and match in text
    ]
    if not hits:
        return None
    # The safe-harbor and prior bullets also contain the current-testing sentence.
    specific = [spec for spec in hits if str(spec["id"]) != "Y3"]
    if specific and any(str(spec["id"]) == "Y3" for spec in hits):
        return specific[0]
    return hits[0]


def _adp_nhce_percent(doc: fitz.Document) -> float | None:
    for page in doc:
        match = _ADP_NHCE.search(page.get_text("text") or "")
        if match:
            return float(match.group(1))
    return None


def _fill_prior_rates(bullet: str, nhce: float | None) -> str:
    """Write the NHCE rate and the HCE maximum into the prior-year recap bullet."""
    if nhce is None:
        return bullet
    hce_label = _percent_label(hce_max_percent(nhce))
    nhce_label = _percent_label(nhce)
    updated = re.sub(
        r"(\bis\s+)(?:\d+(?:\.\d+)?\s*)?%\s*(based on\b)",
        rf"\g<1>{hce_label} \g<2>",
        bullet,
        count=1,
        flags=re.I,
    )
    updated = re.sub(
        r"(\bof\s+)(?:\d+(?:\.\d+)?\s*)?%",
        rf"\g<1>{nhce_label}",
        updated,
        count=1,
        flags=re.I,
    )
    return updated


def _percent_label(value: float) -> str:
    rounded = round(float(value), 2)
    if rounded == int(rounded):
        return f"{int(rounded)}%"
    return f"{rounded:.2f}".rstrip("0").rstrip(".") + "%"


def _split_recap(text: str) -> tuple[str, list[str]]:
    lines = [line.strip() for line in text.splitlines()]
    header: list[str] = []
    bullets: list[str] = []
    current: list[str] = []
    started = False
    for line in lines:
        if re.match(r"^[\u2022•\-\*\?]\s+", line):
            if current:
                bullets.append(" ".join(current).strip())
            started = True
            current = [re.sub(r"^[\u2022•\-\*\?]\s*", "", line)]
            continue
        if not started:
            header.append(line)
            continue
        if line:
            current.append(line)
        elif current:
            bullets.append(" ".join(current).strip())
            current = []
    if current:
        bullets.append(" ".join(current).strip())
    return "\n".join(header).strip() or "Important Information", [item for item in bullets if item]

