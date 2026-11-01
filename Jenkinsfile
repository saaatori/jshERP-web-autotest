// gyj-ui-pytest —— 内联 Pipeline：整段粘贴到任务的 "Pipeline script" 框即可运行，无需 SCM。
// 后续切回 "Pipeline script from SCM" 时同一份内容也可用（不依赖 checkout scm）。
// 前提：Manage Jenkins → Tools 已配置 Allure Commandline（名字 allure-cli）；
//       未配置也不影响构建（报告发布失败仅提示跳过）。
// 数据预置账号依赖被测环境存在 uitest_api 等测试账号：数据库重置后先在
//   项目目录执行 python utils/bootstrap_test_accounts.py 一键重建。
// 注意：WORKSPACE 等变量仅在节点上下文可用，路径一律定义在 environment 块内，
//   不要提到 pipeline {} 外层。

properties([
    parameters([
        string(name: 'PYTEST_MARK', defaultValue: '', description: 'pytest 标记过滤，如 smoke；留空=全量'),
        string(name: 'BROWSER_HEADLESS', defaultValue: 'true', description: '无头模式 true/false')
    ]),
    pipelineTriggers([cron('H 21 * * *')])   // 每晚 21 点低峰；先手动跑稳再保留定时
])

pipeline {
    agent any

    environment {
        // 被测项目工作目录（本机常驻 checkout；内联模式不做 SCM 拉取，回归跑该目录当前内容）
        PROJECT  = 'D:\\PythonProject\\jshERP-web-autotest'
        VENV     = "${WORKSPACE}\\.venv-ci"
        PY       = "${VENV}\\Scripts\\python.exe"
        // config/ui_config.yaml 的 headless 由 HEADLESS 环境变量覆盖（utils/config.py）
        HEADLESS = "${params.BROWSER_HEADLESS ?: 'true'}"
    }

    stages {
        stage('环境') {
            steps {
                echo "被测项目目录: ${PROJECT}"
                bat "python -m venv \"${VENV}\" || py -3.11 -m venv \"${VENV}\""
                bat "\"${PY}\" --version && \"${PY}\" -m pip install -r \"${PROJECT}\\requirements.txt\""
            }
        }
        stage('UI 测试') {
            options {
                timeout(time: 60, unit: 'MINUTES')
            }
            steps {
                // cwd 切到项目目录：pytest.ini（标记/Allure 插件参数）与 data/、config/ 均相对该目录；
                // 命令行 --alluredir 覆盖 addopts，把结果直接写进 Jenkins 工作区供发布
                bat "cd /d ${PROJECT} && \"${PY}\" -m pytest -q ${params.PYTEST_MARK ? "-m ${params.PYTEST_MARK}" : ''} --alluredir=\"${WORKSPACE}\\allure-results\" --clean-alluredir"
            }
        }
    }

    post {
        always {
            // 产物集中拷贝到工作区再归档（失败截图/页面源码/日志）
            bat "if exist \"${PROJECT}\\reports\\screenshots\" xcopy /e /i /y \"${PROJECT}\\reports\\screenshots\" \"${WORKSPACE}\\screenshots\" >nul"
            bat "if exist \"${PROJECT}\\reports\\pages\" xcopy /e /i /y \"${PROJECT}\\reports\\pages\" \"${WORKSPACE}\\pages\" >nul"
            bat "if exist \"${PROJECT}\\logs\" xcopy /e /i /y \"${PROJECT}\\logs\" \"${WORKSPACE}\\logs\" >nul"
            script {
                try {
                    allure includeProperties: false, results: [[path: 'allure-results']]
                } catch (err) {
                    echo "Allure 报告发布跳过（请在 Tools 配置 Allure Commandline，名称 allure-cli）: ${err.message}"
                }
            }
            archiveArtifacts artifacts: 'screenshots/**/*.png,pages/**/*.html,logs/*.log', allowEmptyArchive: true
        }
    }
}
