from __future__ import annotations

import re

import fitz
import yaml

from config.settings import CONFIG_DIR
from models.plan_profile import PlanProfile
from models.review import RuleDecision

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
            if extra and extra.lower() not in page_text.lower():
                continue
            for hit in page.search_for(heading):
                end_y = page.rect.y1 - 36
                for other in headings:
                    if other == heading:
                        continue
                    for rect in page.search_for(other):
                        if rect.y0 > hit.y0 + 8:
                            end_y = min(end_y, rect.y0 - 4)
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


def fill_qnec_placeholders(doc: fitz.Document, profile: PlanProfile) -> list[str]:
    """TEST23 §C: write QNEC amounts onto the CURRENT Excess Return Notice."""
    filled: list[str] = []
    total = profile.total_qnec
    for page in doc:
        original = page.get_text("text") or ""
        if "$X,XXX,XXX.XX" not in original:
            continue
        updated = re.sub(r"\s+", " ", original)
        if total is not None:
            money = _money(total)
            updated = updated.replace(
                "The amount of the QNEC that is required to pass the ADP/ACP test is $X,XXX,XXX.XX",
                f"The amount of the QNEC that is required to pass the ADP/ACP test is {money}",
            )
            updated = updated.replace("ADP/ACP test is $X,XXX,XXX.XX", f"ADP/ACP test is {money}")
            filled.append(f"total={money}")
        if profile.adp_qnec is not None:
            updated = updated.replace(
                "The ADP QNEC is $X,XXX,XXX.XX",
                f"The ADP QNEC is {_money(profile.adp_qnec)}",
            )
            filled.append(f"adp={_money(profile.adp_qnec)}")
        else:
            updated = re.sub(r"The ADP QNEC is \$X,XXX,XXX\.XX\.?\n?", "", updated)
        if profile.acp_qnec is not None:
            updated = updated.replace(
                "The ACP QNEC is $X,XXX,XXX.XX",
                f"The ACP QNEC is {_money(profile.acp_qnec)}",
            )
            filled.append(f"acp={_money(profile.acp_qnec)}")
        else:
            updated = re.sub(r"The ACP QNEC is \$X,XXX,XXX\.XX\.?\n?", "", updated)
        if profile.deferral_refund is not None:
            updated = updated.replace(
                "Deferral Contribution of $X,XXX,XXX.XX",
                f"Deferral Contribution of {_money(profile.deferral_refund)}",
            )
            filled.append(f"deferral={_money(profile.deferral_refund)}")
        else:
            updated = re.sub(r"Deferral Contribution of \$X,XXX,XXX\.XX\.?\s*", "", updated)
        if profile.match_refund is not None:
            updated = updated.replace(
                "Match Contribution of $X,XXX,XXX.XX",
                f"Match Contribution of {_money(profile.match_refund)}",
            )
            filled.append(f"match={_money(profile.match_refund)}")
        else:
            updated = re.sub(r"Match Contribution of \$X,XXX,XXX\.XX\.?\s*", "", updated)
        if updated != original:
            page.add_redact_annot(page.rect, fill=(1, 1, 1), text="")
            page.apply_redactions()
            page.insert_textbox(fitz.Rect(54, 54, 558, 738), updated, fontsize=11, fontname="helv")
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


def apply_recap_bullets(doc: fitz.Document, decisions: list[RuleDecision]) -> list[str]:
    """TEST23 §I: drop unused Important Information bullets and pack the page."""
    specs = _recap_specs()
    if not specs:
        return []
    remove_ids = {item.rule_id for item in decisions if item.action == "remove"}
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
    for spec in specs:
        match = str(spec.get("match") or "").lower()
        if match and match in text:
            return spec
    return None


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

