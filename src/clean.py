"""Inspect the Stack Overflow survey files and write a validation report."""

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_PATH = Path("data/raw/survey_results_public.txt")
DEFAULT_SCHEMA_PATH = Path("data/raw/survey_results_schema.txt")
DEFAULT_REPORT_PATH = Path("data/report/data_validation_report.txt")
MISSING_VALUES = {"", "NA"}


def resolve_project_path(path: str | Path) -> Path:
    """Resolve relative paths from the project root, regardless of cwd."""
    resolved = Path(path).expanduser()
    if not resolved.is_absolute():
        resolved = PROJECT_ROOT / resolved
    return resolved.resolve()


def add_line(lines: list[str], text: object = "") -> None:
    lines.append(str(text))


def run_validation(
    data_path: str | Path = DEFAULT_DATA_PATH,
    schema_path: str | Path = DEFAULT_SCHEMA_PATH,
    report_path: str | Path = DEFAULT_REPORT_PATH,
) -> bool:
    """Validate the public results file against its schema and write a report."""
    data_path = resolve_project_path(data_path)
    schema_path = resolve_project_path(schema_path)
    report_path = resolve_project_path(report_path)

    missing_files = [path for path in (data_path, schema_path) if not path.is_file()]
    if missing_files:
        missing_list = "\n".join(f"- {path}" for path in missing_files)
        raise FileNotFoundError(
            "Required input file(s) were not found. Check the paths or pass "
            "--data and --schema:\n" + missing_list
        )

    with schema_path.open("r", encoding="utf-8-sig", newline="") as file:
        schema_rows = list(csv.DictReader(file))

    schema_columns = [row["column"] for row in schema_rows]
    schema_by_column = {row["column"]: row for row in schema_rows}

    row_count = 0
    response_ids = set()
    duplicate_ids = []
    blank_ids = 0
    bad_width_rows = []
    missing_counts = Counter()
    nonmissing_counts = Counter()

    with data_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.reader(file)
        headers = next(reader, None)
        if not headers:
            raise ValueError(f"The results file is empty or has no header: {data_path}")
        if "ResponseId" not in headers:
            raise ValueError(f"The results file has no ResponseId column: {data_path}")

        response_id_index = headers.index("ResponseId")

        for line_number, row in enumerate(reader, start=2):
            row_count += 1

            if len(row) != len(headers):
                bad_width_rows.append((line_number, len(row), row[:5]))
                continue

            for index, value in enumerate(row):
                column = headers[index]
                if value in MISSING_VALUES:
                    missing_counts[column] += 1
                else:
                    nonmissing_counts[column] += 1

            response_id = row[response_id_index].strip()
            if response_id in MISSING_VALUES:
                blank_ids += 1
            elif response_id in response_ids:
                duplicate_ids.append(response_id)
            else:
                response_ids.add(response_id)

    data_column_set = set(headers)
    schema_column_set = set(schema_columns)
    columns_missing_from_schema = sorted(data_column_set - schema_column_set)
    columns_missing_from_data = sorted(schema_column_set - data_column_set)
    schema_duplicate_columns = sorted(
        column
        for column, count in Counter(schema_columns).items()
        if count > 1
    )

    aiwork_row = schema_by_column.get("AIWorkCurrentlyUse", {})
    aiwork_source_columns = [
        item
        for item in aiwork_row.get("source_columns", "").split(";")
        if item
    ]
    aiimpact_columns = [column for column in headers if column.startswith("AIImpact_")]
    aisat_columns = [column for column in headers if column.startswith("AISat_")]

    nonmissing_count_mismatches = []
    for column in headers:
        schema_row = schema_by_column.get(column)
        if schema_row is None:
            continue

        try:
            expected_nonmissing = int(schema_row.get("nonmissing", ""))
        except (TypeError, ValueError):
            continue

        actual_nonmissing = nonmissing_counts[column]
        if actual_nonmissing != expected_nonmissing:
            nonmissing_count_mismatches.append(
                (column, expected_nonmissing, actual_nonmissing)
            )

    lines = []
    add_line(lines, "Stack Overflow Developer Survey 数据文件验证报告")
    add_line(lines, "=" * 60)
    add_line(lines, f"数据文件：{data_path}")
    add_line(lines, f"数据字典：{schema_path}")
    add_line(lines)

    add_line(lines, "一、数据文件结构")
    add_line(lines, "-" * 60)
    add_line(lines, f"数据行数：{row_count:,}")
    add_line(lines, f"数据列数：{len(headers):,}")
    add_line(lines, f"数据字典字段数：{len(schema_columns):,}")
    add_line(lines, f"数据文件是否包含 valid_response：{'是' if 'valid_response' in data_column_set else '否'}")
    add_line(lines, f"数据文件是否包含 Consent：{'是' if 'Consent' in data_column_set else '否'}")
    add_line(lines, f"数据文件是否包含 is_bot：{'是' if 'is_bot' in data_column_set else '否'}")
    add_line(lines)

    add_line(lines, "二、ResponseId 检查")
    add_line(lines, "-" * 60)
    add_line(lines, f"唯一 ResponseId 数量：{len(response_ids):,}")
    add_line(lines, f"重复 ResponseId 数量：{len(duplicate_ids):,}")
    add_line(lines, f"空 ResponseId 数量：{blank_ids:,}")
    if duplicate_ids:
        add_line(lines, "重复 ResponseId 值：")
        for response_id in sorted(set(duplicate_ids)):
            add_line(lines, f"  {response_id}")
    add_line(lines)

    add_line(lines, "三、每行字段数检查")
    add_line(lines, "-" * 60)
    add_line(lines, f"字段数不匹配的记录数：{len(bad_width_rows):,}")
    if bad_width_rows:
        add_line(lines, "异常记录详情（文件行号、实际字段数、前五个字段值）：")
        for line_number, actual_width, preview in bad_width_rows:
            add_line(lines, f"  行 {line_number}: 有 {actual_width} 列；预览={preview}")
    add_line(lines)

    add_line(lines, "四、数据文件与数据字典字段对照")
    add_line(lines, "-" * 60)
    add_line(lines, f"数据列中有、字典中没有的字段数：{len(columns_missing_from_schema)}")
    for column in columns_missing_from_schema:
        add_line(lines, f"  {column}")
    add_line(lines, f"字典中有、数据列中没有的字段数：{len(columns_missing_from_data)}")
    for column in columns_missing_from_data:
        add_line(lines, f"  {column}")
    add_line(lines, f"数据字典重复字段名数量：{len(schema_duplicate_columns)}")
    for column in schema_duplicate_columns:
        add_line(lines, f"  {column}")
    add_line(lines)

    add_line(lines, "五、项目相关任务字段")
    add_line(lines, "-" * 60)
    add_line(lines, f"AIWorkCurrentlyUse 对应源字段数：{len(aiwork_source_columns)}")
    add_line(lines, f"AIImpact 任务字段数：{len(aiimpact_columns)}")
    add_line(lines, f"AISat 任务字段数：{len(aisat_columns)}")
    add_line(lines, "AIImpact 字段：" + ", ".join(aiimpact_columns))
    add_line(lines, "AISat 字段：" + ", ".join(aisat_columns))
    add_line(lines)

    add_line(lines, "六、所有字段的缺失值统计")
    add_line(lines, "-" * 60)
    add_line(lines, "字段 | 缺失数量 | 缺失比例")
    for column in headers:
        missing = missing_counts[column]
        percentage = missing / row_count * 100 if row_count else 0
        add_line(lines, f"{column} | {missing:,} | {percentage:.2f}%")
    add_line(lines)

    add_line(lines, "七、数据字典非缺失数量对照")
    add_line(lines, "-" * 60)
    add_line(lines, f"非缺失数量不一致的字段数：{len(nonmissing_count_mismatches)}")
    if nonmissing_count_mismatches:
        add_line(lines, "字段 | 字典非缺失数 | 实际非缺失数")
        for column, expected, actual in nonmissing_count_mismatches:
            add_line(lines, f"{column} | {expected:,} | {actual:,}")
    else:
        add_line(lines, "所有可对照字段的非缺失数量均与数据字典一致。")
    add_line(lines)

    checks = [
        ("数据行数为 30,903", row_count == 30_903),
        ("数据列数为 212", len(headers) == 212),
        ("字典字段数为 212", len(schema_columns) == 212),
        ("没有重复 ResponseId", len(duplicate_ids) == 0),
        ("没有空 ResponseId", blank_ids == 0),
        ("每行字段数一致", len(bad_width_rows) == 0),
        ("数据字段都能在字典中找到", len(columns_missing_from_schema) == 0),
        ("字典字段都能在数据中找到", len(columns_missing_from_data) == 0),
        ("AIWorkCurrentlyUse 对应 19 个源字段", len(aiwork_source_columns) == 19),
        ("AIImpact 有 7 个任务字段", len(aiimpact_columns) == 7),
        ("AISat 有 7 个任务字段", len(aisat_columns) == 7),
    ]
    failed_checks = [name for name, passed in checks if not passed]

    add_line(lines, "八、自动验证结果")
    add_line(lines, "-" * 60)
    for name, passed in checks:
        add_line(lines, f"[{'通过' if passed else '未通过'}] {name}")
    if failed_checks:
        add_line(lines)
        add_line(lines, "未通过项目：")
        for name in failed_checks:
            add_line(lines, f"  - {name}")
    else:
        add_line(lines)
        add_line(lines, "所有自动验证均通过。")

    # Create the report directory if it does not exist, then save the report.
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"完整报告已保存到：{report_path}")
    print(f"自动验证结果：{'全部通过' if not failed_checks else f'{len(failed_checks)} 项未通过'}")
    return not failed_checks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate the survey results file against its schema."
    )
    parser.add_argument("--data", default=DEFAULT_DATA_PATH, help="Results file path")
    parser.add_argument("--schema", default=DEFAULT_SCHEMA_PATH, help="Schema file path")
    parser.add_argument("--report", default=DEFAULT_REPORT_PATH, help="Report output path")
    args = parser.parse_args(argv)

    try:
        return 0 if run_validation(args.data, args.schema, args.report) else 1
    except (FileNotFoundError, ValueError, csv.Error) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
