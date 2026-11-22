## 一、参考项目

- 参考项目的GitHub 仓库：[https://github.com/StackExchange/Survey]
- 问卷预览页：[https://stackoverflow-survey-preview.netlify.app/#q-Welcome]

## 二、建议重新组织项目结构

- 所有文件都放在同级根目录下，跟老师在unit5提供的三个参考案例一样；
- 只用**一个** `group_project.ipynb`，所有代码都放在这里；
- 两个csv 文件过大GitHub传输不了，需要组员各自去参考项目的GitHub仓库自行下载两个csv文件；
- 代码总量 **不超过 500 行**
- **大家合并代码之前，记得把各自的文件读取路径改一下，项目结构改了以后可能文件读取路径会不一样**

## 三、下载csv文件时注意不要下成txt版本

- 点文件 → **View raw** → Ctrl+S，浏览器会把csv文件下载到本地（否则拿到 txt）

## 四、AD可以统一的口径要点

- 不按 `CodeMain` 筛人，全保留
- 19 个任务用问卷原英文名，按 `;` 拆（不能用逗号）
- 某任务标了"不在我的工作流程" → 该任务不算分母，其他任务照留
- `Not applicable` 是有效回答，不算缺失，不等于"不用"
- 缺失多是跳题造成的，属结构性缺失，不补不删
- **不统一清洗**：各自清洗自己那份数据
- 每人写清：用了哪些字段、谁能回答、缺失怎么判、样本 N 多少、冲突怎么排


## 五、我的AI给的参考流程



```text
survey_results_public.csv + survey_results_schema.csv
                       ↓
      数据原样入库，不作统一清洗：SQLite survey.db
             responses + columns_meta
                       ↓
        A / B / C / D 各自登记题目与口径
                       ↓
           各自 SQL 取数 → 独立处理
                       ↓
 A 当前使用 | B 有用程度 | C 满意度变化 | D 未来意愿
                       ↓
        各自统计与图表 → 汇总解释与结论
```


数据库不用装软件，Python 自带 `sqlite3`，约 70 行。
