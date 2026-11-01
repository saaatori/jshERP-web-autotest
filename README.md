# 管伊佳 ERP Web UI 自动化测试（项目二）

Python + Selenium + Pytest + Allure + logging + Excel 关键字驱动 + PO 模式的 Web UI 自动化仓库。

- 上游文档：`F:\jsh-ERP-test`（需求分析 V1.6 / 项目二测试计划 V1.3 / WebUI 测试用例 59 条）
- 被测系统：管伊佳 ERP V3.6（commit 8f5dc08），前端 http://127.0.0.1:3001
- 浏览器：Chrome 156 + Selenium Manager 自动匹配驱动（版本锁定策略见计划 §4）

## 框架结构

```text
jshERP-web-autotest/
├── config/ui_config.yaml        # base_url、浏览器、等待、账号
├── data/
│   ├── ui_cases.xlsx            # 自动化用例登记表（37 条，含关键字步骤/节点）
│   └── keywords.xlsx            # 关键字定义
├── page/                        # PO 层：BasePage + 各业务 Page Object
│   ├── base_page.py             # 显式等待/点击降级/AntD组件/表格/截图
│   ├── login_page.py  menu_frame.py
│   ├── material_page.py  crud_page.py（供应商/客户/仓库/账户）
│   ├── bill_page.py             # 单据通用列表+编辑器（采购/销售/零售/调拨/财务）
│   └── stock_report_page.py
├── keywords/executor.py         # Excel 关键字反射分发（打开/登录/输入/点击/断言…）
├── testcases/                   # Pytest 用例（模块=需求分析模块序）
│   ├── test_login.py  test_menu_frame.py
│   ├── test_material.py  test_crud.py
│   ├── test_purchase.py  test_sale.py
│   ├── test_dep_ret_fin.py  test_common.py
│   ├── test_zz_permission.py    # 权限（命名 zz 保证最后执行，切换账号）
│   └── test_excel_driver.py     # Excel 驱动入口
├── utils/                       # config/logger/driver/api_helper(数据准备后门)/excel
├── conftest.py                  # driver 会话/管理员登录/失败取证(截图+页面源码)
├── pytest.ini  requirements.txt  Jenkinsfile
└── reports/  logs/              # 产物（git 忽略）
```

## 关键设计（与计划的对应）

- **显式等待优先，禁裸 sleep 决策化**：BasePage 全部操作走 WebDriverWait；仅路由渲染等固定间隔用短 sleep 并注明原因。
- **AntD 组件封装**：下拉（含 antd v3 搜索框、可搜索/普通两种）、确认弹窗、通知/新手引导（intro.js）清理、div.tr 明细网格（Portal 于 modal 外，JS 标记定位）。
- **JS 点击降级**：背景动画/浮层遮挡导致 ElementClickInterceptedException 时降级 JS click（登录页实测）。
- **数据后门**：`utils/api_helper.py` 封装项目一接口约定（MD5 登录、X-Access-Token、请求间隔 1.2s 防 DEF-EXP-06 防攻击误杀），UI 用例的数据预置/清理全部走接口。
- **失败取证**：pytest 钩子自动截图 + 页面源码 + Allure 附件。
- **测试数据隔离**：UITEST_ 前缀 + 动态后缀，teardown 恢复（含 minus_stock_flag 开关翻转用例）。

## 运行

```bash
pip install -r requirements.txt
# 冒烟
pytest -m smoke
# 全量
pytest
# Allure 报告
pytest --alluredir=allure-results --clean-alluredir
allure generate allure-results -o reports/allure-report --clean
```

标记：`smoke` / `regression` / `permission` / `db_check`（见 pytest.ini）。

## 执行结果（2026-10-28/29，commit 8f5dc08 环境）

| 轮次 | 结果 | 时长 |
| --- | --- | --- |
| 全量第 1 轮 | **41 通过 / 0 失败**（codecase 由 Excel 登记跳过） | 13m04s |
| 全量第 2 轮（背靠背） | **41 通过 / 0 失败** | 13m14s |
| 全量第 3 轮（补 RET-002×2/COM-001/SALE-006 登记后） | **44 通过 / 0 失败** | 14m32s |

连续三轮无环境性偶发失败，满足测试计划准出条件第 3 条。

覆盖（自动化 41 条代码用例 + 3 条 Excel 关键字驱动）：登录 5、主框架 2、商品 4、基础资料 4、采购 8、销售 7、仓库报表 3、零售 3、财务 1、权限 4、通用交互 1 + Excel 驱动 3。报告：`reports/allure-report/index.html`。

## 实测记录与缺陷候选（禅道跟踪）

| 编号 | 现象 | 影响 |
| --- | --- | --- |
| DEF-UI-002 | 用户级仓库绑定（API 建立）在单据编辑器仓库下拉未生效，未授权/已删除仓库均可见 | 权限 |
| DEF-EXP-01 | 会员期初预存被余额重算覆盖（预存100消费20后余额-20，应为80） | 资金数据 |

> 排查期间曾误报 4 个缺陷（菜单接口 500 / btnStr 触发 500 / 按钮位不生效 / 条码重复无提示），
> 复核确认均为测试手段问题（接口裸调缺 body、提示形态未覆盖 Tooltip），已撤销并归档为教训——
> 见 `docs/问题与解决方案.md` 第四节。

另：DEF-EXP-06（防攻击机制同秒双操作强制注销）导致全量回归时接口建数与浏览器操作
同用户互踩，框架层以**独立接口账号 uitest_api**（管理员角色）与浏览器会话隔离。

各缺陷的实测注记已写入对应用例 docstring 与 Allure 描述；预期结果以系统实际行为为准回填用例。五个缺陷的禅道提交底稿（标题/类型/严重程度/优先级/重现步骤/预期/实际/关键词）见 [docs/缺陷提交清单.md](docs/缺陷提交清单.md)。

框架搭建与调试过程中的全部问题、根因与解决方法（含排查方法论）详见 [docs/问题与解决方案.md](docs/问题与解决方案.md)。

## Excel 驱动

`data/ui_cases.xlsx` 登记全部 37 条自动化用例（上游 59 条中的自动化子集）：
`执行方式=keyword` 由 `testcases/test_excel_driver.py` 按关键字步骤驱动；
`执行方式=codecase` 的复杂链路由同编号 pytest 代码用例承载（驱动入口 skip，Excel 为追溯源）。

## Jenkins

`gyj-ui-pytest`：每晚低峰 Chrome Headless 执行（`headless: true`），Allure 归档见 Jenkinsfile。
