import logging
import re
from copy import copy
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.formula.translate import Translator
from openpyxl.utils import column_index_from_string, get_column_letter
from openpyxl.utils.cell import range_boundaries
from openpyxl.workbook.properties import CalcProperties

from app.services.excel.excel_config import (
    ENTRY_HEADER_NAME,
    HEADER_ROW,
    NEW_COLUMN_DEFAULT_VALUE,
    NEW_COLUMN_HEADER,
)

logger = logging.getLogger(__name__)

# $AI$4, $AI$ (defined names)
_DOLLAR_COL_DOLLAR = re.compile(r"\$([A-Z]{1,3})\$")
# $AI: in $AI:$AI (whole-column refs)
_DOLLAR_COL_COLON = re.compile(r"\$([A-Z]{1,3}):")
# :$AI at end of string ($AI:$AI)
_TRAILING_COLON_DOLLAR_COL = re.compile(r":\$([A-Z]{1,3})$")


class ExcelProcessor:
    def process(self, source_path: Path, output_path: Path) -> dict[str, str | int]:
        if not source_path.is_file():
            raise FileNotFoundError(f"Source file not found: {source_path}")

        logger.info("Processing Excel file: %s", source_path.name)

        workbook = load_workbook(source_path, data_only=False)
        worksheet = workbook.active

        entry_col = self._find_entry_column(worksheet)
        if entry_col is None:
            workbook.close()
            raise ValueError(
                f'Column "{ENTRY_HEADER_NAME}" not found in row {HEADER_ROW}'
            )

        new_col = entry_col + 1
        if self._column_has_content(worksheet, new_col):
            worksheet.insert_cols(new_col)
            self._repair_after_column_insert(workbook, worksheet, new_col)
        else:
            logger.info("Column %s is empty; writing in place without insert_cols", new_col)

        worksheet.cell(row=HEADER_ROW, column=new_col, value=NEW_COLUMN_HEADER)
        self._copy_header_style(worksheet, entry_col, new_col)

        rows_updated = 0
        last_data_row = self._find_last_data_row(worksheet, entry_col)
        for row in range(HEADER_ROW + 1, last_data_row + 1):
            if not self._row_should_receive_value(worksheet, row, entry_col, new_col):
                continue
            worksheet.cell(row=row, column=new_col, value=NEW_COLUMN_DEFAULT_VALUE)
            rows_updated += 1

        self._configure_excel_recalc_on_open(workbook)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        sheet_name = worksheet.title
        workbook.save(output_path)
        workbook.close()

        logger.info(
            "Saved processed file: %s (rows updated: %s)",
            output_path.name,
            rows_updated,
        )

        return {
            "sheet_name": sheet_name,
            "entry_column_index": entry_col,
            "new_column_index": new_col,
            "new_column_header": NEW_COLUMN_HEADER,
            "rows_updated": rows_updated,
        }

    def _repair_after_column_insert(
        self, workbook, worksheet, insert_col: int, amount: int = 1
    ) -> None:
        """Fix formulas, merges, and named ranges after openpyxl insert_cols."""
        self._translate_formulas_after_column_insert(worksheet, insert_col, amount)
        self._translate_formulas_before_insert_column(worksheet, insert_col, amount)
        self._adjust_merged_cells_after_column_insert(worksheet, insert_col, amount)
        self._adjust_defined_names_after_column_insert(workbook, insert_col, amount)

    def _configure_excel_recalc_on_open(self, workbook) -> None:
        calc_id = 191028
        if workbook.calculation is not None and workbook.calculation.calcId:
            calc_id = workbook.calculation.calcId
        workbook.calculation = CalcProperties(
            calcId=calc_id,
            calcMode="auto",
            fullCalcOnLoad=True,
            calcOnSave=True,
        )

    def _find_entry_column(self, worksheet) -> int | None:
        for col in range(1, worksheet.max_column + 1):
            value = worksheet.cell(row=HEADER_ROW, column=col).value
            if value is None:
                continue
            if str(value).strip().lower() == ENTRY_HEADER_NAME.lower():
                return col
        return None

    def _column_has_content(self, worksheet, col: int) -> bool:
        for row in range(HEADER_ROW, worksheet.max_row + 1):
            cell = worksheet.cell(row=row, column=col)
            if cell.data_type == "f" and cell.value:
                return True
            if cell.value is not None and str(cell.value).strip() != "":
                return True
        return False

    def _find_last_data_row(self, worksheet, entry_col: int) -> int:
        last_row = HEADER_ROW
        for row in range(HEADER_ROW + 1, worksheet.max_row + 1):
            if self._row_has_meaningful_content(worksheet, row, entry_col):
                last_row = row
        return max(last_row, HEADER_ROW + 1)

    def _row_has_meaningful_content(self, worksheet, row: int, entry_col: int) -> bool:
        for col in range(1, worksheet.max_column + 1):
            cell = worksheet.cell(row=row, column=col)
            if cell.data_type == "f" and cell.value:
                return True
            if cell.value is None:
                continue
            if str(cell.value).strip() != "":
                return True
        return False

    def _row_should_receive_value(
        self, worksheet, row: int, entry_col: int, new_col: int
    ) -> bool:
        if self._is_summary_row(worksheet, row):
            return False

        entry_value = worksheet.cell(row=row, column=entry_col).value
        if entry_value is not None and str(entry_value).strip() != "":
            return True

        return False

    def _is_summary_row(self, worksheet, row: int) -> bool:
        for col in range(1, min(worksheet.max_column, 5) + 1):
            value = worksheet.cell(row=row, column=col).value
            if value is None:
                continue
            text = str(value).strip().lower()
            if "total" in text:
                return True
        return False

    def _copy_header_style(self, worksheet, from_col: int, to_col: int) -> None:
        source = worksheet.cell(row=HEADER_ROW, column=from_col)
        target = worksheet.cell(row=HEADER_ROW, column=to_col)
        if source.has_style:
            target.font = copy(source.font)
            target.border = copy(source.border)
            target.fill = copy(source.fill)
            target.number_format = copy(source.number_format)
            target.protection = copy(source.protection)
            target.alignment = copy(source.alignment)

    def _translate_formulas_after_column_insert(
        self, worksheet, insert_col: int, amount: int = 1
    ) -> None:
        max_col = worksheet.max_column + amount
        for row in range(1, worksheet.max_row + 1):
            for col in range(insert_col + amount, max_col + 1):
                cell = worksheet.cell(row=row, column=col)
                if cell.data_type != "f" or not cell.value:
                    continue
                old_col = col - amount
                old_coord = f"{get_column_letter(old_col)}{row}"
                try:
                    cell.value = Translator(cell.value, old_coord).translate_formula(
                        col_delta=amount
                    )
                except Exception as exc:
                    logger.warning(
                        "Could not translate formula at %s: %s",
                        cell.coordinate,
                        exc,
                    )

    def _translate_formulas_before_insert_column(
        self, worksheet, insert_col: int, amount: int = 1
    ) -> None:
        """Shift column references in formulas that stayed in columns left of the insert."""
        for row in range(1, worksheet.max_row + 1):
            for col in range(1, insert_col):
                cell = worksheet.cell(row=row, column=col)
                if cell.data_type != "f" or not cell.value:
                    continue
                shifted = self._shift_formula_column_references(
                    cell.value, insert_col, amount
                )
                if shifted != cell.value:
                    cell.value = shifted

    def _shift_formula_column_references(
        self, formula: str, insert_col: int, amount: int
    ) -> str:
        if not isinstance(formula, str) or not formula.startswith("="):
            return formula

        pattern = re.compile(r"(\$?)([A-Z]{1,3})(\$?)(\d+)")

        def smart_repl(match: re.Match[str]) -> str:
            col_letters = match.group(2)
            col_idx = column_index_from_string(col_letters)
            if col_idx >= insert_col:
                col_idx += amount
            return (
                f"{match.group(1)}{get_column_letter(col_idx)}{match.group(3)}{match.group(4)}"
            )

        return pattern.sub(smart_repl, formula)

    def _adjust_merged_cells_after_column_insert(
        self, worksheet, insert_col: int, amount: int = 1
    ) -> None:
        merged_ranges = list(worksheet.merged_cells.ranges)
        for merged_range in merged_ranges:
            worksheet.unmerge_cells(str(merged_range))

        for merged_range in merged_ranges:
            min_col, min_row, max_col, max_row = range_boundaries(str(merged_range))
            if min_col >= insert_col:
                min_col += amount
                max_col += amount
            elif max_col >= insert_col:
                max_col += amount
            worksheet.merge_cells(
                start_row=min_row,
                start_column=min_col,
                end_row=max_row,
                end_column=max_col,
            )

    def _adjust_defined_names_after_column_insert(
        self, workbook, insert_col: int, amount: int = 1
    ) -> None:
        if not workbook.defined_names:
            return

        for name in list(workbook.defined_names):
            defn = workbook.defined_names[name]
            if not defn.attr_text:
                continue
            shifted = self._shift_column_refs_in_range(defn.attr_text, insert_col, amount)
            if shifted != defn.attr_text:
                logger.info("Defined name %s shifted: %s", name, defn.attr_text)
                defn.attr_text = shifted

    def _shift_col_letter(self, col_letter: str, insert_col: int, amount: int) -> str:
        col_idx = column_index_from_string(col_letter)
        if col_idx >= insert_col:
            col_idx += amount
        return get_column_letter(col_idx)

    def _shift_column_refs_in_range(
        self, text: str, insert_col: int, amount: int
    ) -> str:
        def repl_dcd(match: re.Match[str]) -> str:
            col = self._shift_col_letter(match.group(1), insert_col, amount)
            return f"${col}$"

        def repl_dcc(match: re.Match[str]) -> str:
            col = self._shift_col_letter(match.group(1), insert_col, amount)
            return f"${col}:"

        def repl_cdc(match: re.Match[str]) -> str:
            col = self._shift_col_letter(match.group(1), insert_col, amount)
            return f":${col}"

        text = _DOLLAR_COL_DOLLAR.sub(repl_dcd, text)
        text = _DOLLAR_COL_COLON.sub(repl_dcc, text)
        text = _TRAILING_COLON_DOLLAR_COL.sub(repl_cdc, text)
        return text
