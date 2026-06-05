pipeline {
    agent any

    environment {
        ORANGEHRM_URL = 'http://host.docker.internal:8080'
    }

    stages {
        stage('拉取代码') {
            steps {
                checkout scm
            }
        }

        stage('安装依赖') {
            steps {
                 sh '''
                    pip3 install -r requirements.txt --break-system-packages --ignore-installed -i https://pypi.tuna.tsinghua.edu.cn/simple --timeout 120 --retries 3
                '''
            }
        }

        stage('运行全部接口测试') {
            steps {
                sh 'python3 RunMain/run.py'
            }
        }
    }

    post {
        always {
            allure([
                includeProperties: false,
                jdk: '',
                properties: [],
                reportBuildPolicy: 'ALWAYS',
                results: [[path: 'Reports/ALLURE/Report']]
            ])
        }
    }
}