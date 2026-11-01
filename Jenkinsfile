pipeline {
    agent any

    parameters {
        string(name: 'PYTEST_MARK', defaultValue: '', description: 'pytest 标记过滤，如 smoke；留空=全量')
        string(name: 'BROWSER_HEADLESS', defaultValue: 'true', description: '无头模式 true/false')
    }

    environment {
        HEADLESS = "${params.BROWSER_HEADLESS}"
    }

    stages {
        stage('环境') {
            steps {
                bat 'python --version'
                bat 'pip install -r requirements.txt'
            }
        }
        stage('UI 测试') {
            steps {
                bat "pytest -q ${params.PYTEST_MARK ? '-m ' + params.PYTEST_MARK : ''} --alluredir=allure-results"
            }
        }
    }

    post {
        always {
            allure includeProperties: false, jdk: '', results: [[path: 'allure-results']]
            archiveArtifacts artifacts: 'reports/screenshots/*.png,logs/*.log', allowEmptyArchive: true
        }
    }
}
