import csv
from collections import Counter
from pathlib import Path

data_path = Path(r"data\raw\survey_results_public.txt")
schema_path = Path(r"data\raw\survey_results_schema.txt")
report_path = Path(r"data\report\data_validation_report.txt")

MISSING_VALUES = {"", "NA"}

# 先检查输入文件是否存在，避免生成不完整报告
for path in (data_path, schema_path):
    if not path.exists():
        raise FileNotFoundError(f"找不到文件：{path}")

# 读取数据字典
with schema_path.open("r", encoding="utf-8-sig", newline="") as f:
    schema_rows = list(csv.DictReader(f))

schema_columns = [row["column"] for row in schema_rows]
schema_by_column = {row["column"]: row for row in schema_rows}

# 流式检查数据文件
row_count = 0
response_ids = set()
duplicate_ids = []
blank_ids = 0
bad_width_rows = []
missing_counts = Counter()
nonmissing_counts = Counter()

with data_path.open("r", encoding="utf-8-sig", newline="") as f:
    reader = csv.reader(f)
    headers = next(reader)

    if "ResponseId" not in headers:
        raise ValueError("数据文件中找不到 ResponseId 列")

    response_id_index = headers.index("ResponseId")

    for line_number, row in enumerate(reader, start=2):
        row_count += 1

        if len(row) != len(headers):
            bad_width_rows.append(
                (line_number, len(row), row[:5])
            )
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

# 对照数据列和字典
data_column_set = set(headers)
schema_column_set = set(schema_columns)

columns_missing_from_schema = sorted(data_column_set - schema_column_set)
columns_missing_from_data = sorted(schema_column_set - data_column_set)

schema_duplicate_columns = sorted(
    column for column, count in Counter(schema_columns).items()
    if count > 1
)

# 核对项目相关字段
aiwork_row = schema_by_column.get("AIWorkCurrentlyUse", {})
aiwork_source_columns = [
    item for item in aiwork_row.get("source_columns", "").split(";")
    if item
]

aiimpact_columns = [
    column for column in headers
    if column.startswith("AIImpact_")
]
aisat_columns = [
    column for column in headers
    if column.startswith("AISat_")
]

# 对照数据字典的非缺失数量与实际统计
nonmissing_count_mismatches = []

for column in headers:
    schema_row = schema_by_column.get(column)

    if schema_row is None:
        continue

    schema_value = schema_row.get("nonmissing", "")

    try:
        expected_nonmissing = int(schema_value)
    except (TypeError, ValueError):
        continue

    actual_nonmissing = nonmissing_counts[column]

    if actual_nonmissing != expected_nonmissing:
        nonmissing_count_mismatches.append(
            (column, expected_nonmissing, actual_nonmissing)
        )

# 收集检查结果
lines = []

def add(text=""):
    lines.append(str(text))

add("Stack Overflow Developer Survey 数据文件验证报告")
add("=" * 60)
add(f"数据文件：{data_path.resolve()}")
add(f"数据字典：{schema_path.resolve()}")
add()

add("一、数据文件结构")
add("-" * 60)
add(f"数据行数：{row_count:,}")
add(f"数据列数：{len(headers):,}")
add(f"数据字典字段数：{len(schema_columns):,}")
add(f"数据文件是否包含 valid_response：{'是' if 'valid_response' in data_column_set else '否'}")
add(f"数据文件是否包含 Consent：{'是' if 'Consent' in data_column_set else '否'}")
add(f"数据文件是否包含 is_bot：{'是' if 'is_bot' in data_column_set else '否'}")
add()

add("二、ResponseId 检查")
add("-" * 60)
add(f"唯一 ResponseId 数量：{len(response_ids):,}")
add(f"重复 ResponseId 数量：{len(duplicate_ids):,}")
add(f"空 ResponseId 数量：{blank_ids:,}")
if duplicate_ids:
    add("重复 ResponseId 值：")
    for response_id in sorted(set(duplicate_ids)):
        add(f"  {response_id}")
add()

add("三、每行字段数检查")
add("-" * 60)
add(f"字段数不匹配的记录数：{len(bad_width_rows):,}")
if bad_width_rows:
    add("异常记录详情（文件行号、实际字段数、前五个字段值）：")
    for line_number, actual_width, preview in bad_width_rows:
        add(f"  行 {line_number}: {actual_width} 列；预览={preview}")
add()

add("四、数据文件与数据字典字段对照")
add("-" * 60)
add(f"数据列中有、字典中没有的字段数：{len(columns_missing_from_schema)}")
for column in columns_missing_from_schema:
    add(f"  {column}")

add(f"字典中有、数据列中没有的字段数：{len(columns_missing_from_data)}")
for column in columns_missing_from_data:
    add(f"  {column}")

add(f"数据字典重复字段名数量：{len(schema_duplicate_columns)}")
for column in schema_duplicate_columns:
    add(f"  {column}")
add()

add("五、项目相关任务字段")
add("-" * 60)
add(f"AIWorkCurrentlyUse 对应源字段数：{len(aiwork_source_columns)}")
add(f"AIImpact 任务字段数：{len(aiimpact_columns)}")
add(f"AISat 任务字段数：{len(aisat_columns)}")
add("AIImpact 字段：" + ", ".join(aiimpact_columns))
add("AISat 字段：" + ", ".join(aisat_columns))
add()

add("六、所有字段的缺失值统计")
add("-" * 60)
add("字段 | 缺失数量 | 缺失比例")
add("-" * 60)

for column in headers:
    missing = missing_counts[column]
    percentage = missing / row_count * 100 if row_count else 0
    add(f"{column} | {missing:,} | {percentage:.2f}%")
add()

add("七、数据字典非缺失数量对照")
add("-" * 60)
add(f"非缺失数量不一致的字段数：{len(nonmissing_count_mismatches)}")
if nonmissing_count_mismatches:
    add("字段 | 字典非缺失数 | 实际非缺失数")
    for column, expected, actual in nonmissing_count_mismatches:
        add(f"{column} | {expected:,} | {actual:,}")
else:
    add("所有可对照字段的非缺失数量均与数据字典一致。")
add()

# 汇总验证状态；先写报告，再根据结果判断是否通过
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

add("八、自动验证结果")
add("-" * 60)
for name, passed in checks:
    add(f"[{'通过' if passed else '未通过'}] {name}")

if failed_checks:
    add()
    add("未通过项目：")
    for name in failed_checks:
        add(f"  - {name}")
else:
    add()
    add("所有自动验证均通过。")

# 保存完整报告
report_path.parent.mkdir(parents=True, exist_ok=True)
report_path.write_text("\n".join(lines), encoding="utf-8")

# 同时在控制台显示报告位置和自动检查结果
print(f"完整报告已保存到：{report_path.resolve()}")
print(f"自动验证结果：{'全部通过' if not failed_checks else f'{len(failed_checks)} 项未通过'}")

if failed_checks:
    raise AssertionError(
        "部分验证未通过，请查看报告文件："
        f"{report_path.resolve()}"
    )