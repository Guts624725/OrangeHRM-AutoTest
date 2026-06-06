pipeline {
    agent any

    parameters {
        choice(
            name: 'TEST_TYPE',
            choices: ['http', 'web'],
            description: '选择测试类型：http(接口自动化) / web(Web UI自动化)'
        )
    }

    stages {
        stage('检出代码') {
            steps {
                checkout scm
            }
        }

        stage('准备配置文件') {
            steps {
                script {
                    // 根据参数自动选择配置文件
                    def configFile = params.TEST_TYPE == 'web' ? '配置文件_web.ini' : '配置文件_http.ini'

                    sh """
                        mkdir -p Config
                        cp /var/jenkins_home/secrets/${configFile} Config/配置文件.ini
                        echo "✅ 已加载配置: ${configFile}"
                    """

                    // 验证配置内容
                    sh '''
                        echo "=== 当前配置 ==="
                        grep -E "AUTO_TYPE|TEST_PROJECT|TEST_URL" Config/配置文件.ini || true
                    '''

                    // Web 测试额外检查 Selenium Grid
                    if (params.TEST_TYPE == 'web') {
                        sh '''
                            echo "🔍 检查 Selenium Grid 连通性..."
                            GRID_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://192.168.1.3:4444/wd/hub/status || echo "000")
                            if [ "$GRID_STATUS" = "200" ]; then
                                echo "✅ Selenium Grid 就绪"
                            else
                                echo "⚠️ 警告：Grid 未响应 (状态码: $GRID_STATUS)，请确认已执行："
                                echo "   docker run -d -p 4444:4444 --shm-size=2g selenium/standalone-chrome"
                            fi
                        '''
                    }
                }
            }
        }

        stage('安装依赖') {
            steps {
                sh '''
                    pip3 install -r requirements.txt \
                        --break-system-packages \
                        --ignore-installed \
                        -i https://pypi.tuna.tsinghua.edu.cn/simple \
                        --timeout 120 --retries 3
                '''
            }
        }

        stage('运行测试') {
            steps {
                sh '''
                    python3 RunMain/run.py
                '''
            }
        }
    }
    
    post {
        always {
            // Allure 报告（路径必须和 run.py 生成的一致）
            allure includeProperties: false, jdk: '', results: [[path: 'Reports/ALLURE/Result']]
        }

        success {
            echo '✅ 构建成功！'
        }

        failure {
            echo '❌ 构建失败，请查看 Console Output 排查问题'
        }
    }
}