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
                    python3 -m pip install --upgrade pip --break-system-packages
                    pip3 install -r requirements.txt --break-system-packages
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