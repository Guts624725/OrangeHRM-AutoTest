pipeline {
    agent any

    stages {
        stage('拉取代码') {
            steps {
                checkout scm
            }
        }

        stage('准备配置文件') {
            steps {
                sh '''
                    mkdir -p Config
                    cp /var/jenkins_home/secrets/配置文件.ini Config/配置文件.ini
                '''
            }
        }

        stage('安装依赖') {
            steps {
                sh 'pip3 install -r requirements.txt --break-system-packages --ignore-installed -i https://pypi.tuna.tsinghua.edu.cn/simple --timeout 120 --retries 3'
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
            allure includeProperties: false, jdk: '', results: [[path: 'REPORTS/ALLURE/REPORT']]
        }
    }
}