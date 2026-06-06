"""
@Author  : 谢胜强
@Time    : 2026/5/7 22:35
@Desc    : Web自动化通用基类
            全平台通用：原生HTML / Vue / React / Angular
            封装元素定位、元素操作、窗口切换、下拉框、JS执行等通用方法
"""
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select
from selenium.webdriver.common.action_chains import ActionChains

from Base.baseData import DataBase
from Base.baseLogger import Logger

from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, \
    ElementNotInteractableException, StaleElementReferenceException, NoSuchElementException, NoAlertPresentException

logger = Logger("baseAutoWeb.py").getLogger()

class WebBase(DataBase):
    """Web自动化通用基类（适配所有Web系统）"""

    def __init__(self, yamlName):
        super().__init__(yamlName)
        self.driver = self.gm.get_value("driver")
        self.default_timeout = 13
        self.poll_interval = 0.5

    def get_locator_data(self, locator, change_data=None):
        """
        从yaml获取元素定位信息
        :param locator: 格式 "page/element"
        :param change_data: 动态替换数据
        :return: 定位元组 (By.XX, value)
        """
        res = self.get_element_data(change_data)
        page, ele = locator.split("/")
        return tuple(res[page][ele])

    def findElement(self, locator, change_data=None, timeout=None):
        """
        单个元素定位（通用版）
        :param timeout: 自定义超时时间，不填则使用默认10s
        """
        try:
            locator = self.get_locator_data(locator, change_data)
            if not isinstance(locator, tuple):
                logger.error("locator必须是元组类型，示例：('id','xxx')")
                raise TypeError("定位参数类型错误")

            # 这里用 visibility 而不是 presence，因为 presence 只保证元素在 DOM 里
            # 但元素可能还不可见（比如被 v-if 控制着，或者 display:none），直接操作会报错
            wait_time = timeout if timeout else self.default_timeout
            logger.debug(f"定位元素：方式={locator[0]}, 值={locator[1]}, 超时={wait_time}s")

            ele = WebDriverWait(self.driver, wait_time, self.poll_interval).until(
                EC.visibility_of_element_located(locator)
            )
            return ele
        except Exception as e:
            logger.error(f"元素定位失败：{locator}")
            raise e

    def findElements(self, locator, change_data=None, timeout=None):
        """批量元素定位（通用版）"""
        try:
            locator = self.get_locator_data(locator, change_data)
            wait_time = timeout if timeout else self.default_timeout

            ele_list = WebDriverWait(self.driver, wait_time, self.poll_interval).until(
                EC.visibility_of_any_elements_located(locator)
            )
            logger.debug(f"批量定位元素{locator}成功，共{len(ele_list)}个")
            return ele_list
        except Exception as e:
            logger.error(f"批量元素定位失败：{locator}")
            raise e

    def is_text_present(self, text):
        """判断页面是否包含指定文本，模糊包含即可"""
        # 强制等1秒，因为有些页面是异步渲染的，立即查 page_source 可能还是旧内容
        # 之前踩过坑：删除操作后马上查文本，结果查的是删除前的页面源码
        time.sleep(1)
        page_all_text = self.driver.page_source
        return text in page_all_text

    def get_url(self, url):
        """打开URL并最大化窗口"""
        self.driver.get(url)
        self.driver.maximize_window()
        logger.debug(f"访问地址：{url}")

    def click(self, locator, change_data=None, timeout=None, retry_times=3, retry_interval=0.5):
        """
        通用点击方法（兼容所有前端框架，支持重试、JS降级和滚动）
        """
        # 注意这里用 is not None，因为 timeout=0 是有意义的（立即失败，不等待）
        # 如果写成 if timeout else，传 0 会被当成 False 处理，永远用默认 10 秒
        _timeout = timeout if timeout is not None else self.default_timeout
        loc = self.get_locator_data(locator, change_data)
        last_exception = None

        for retry in range(retry_times):
            try:
                # 关键：element_to_be_clickable 传的是定位器元组，不是已经查到的元素
                # 如果传元素，等待就失去意义了，因为元素在进循环前就已经陈旧了
                wait = WebDriverWait(self.driver, _timeout, self.poll_interval)
                ele = wait.until(EC.element_to_be_clickable(loc))

                # 先滚到视野中间，很多前端框架（比如 ElementUI）按钮在视口外时
                # 虽然 element_to_be_clickable 返回 True，但 click 会被拦截
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center', inline: 'center'});",
                    ele
                )
                time.sleep(0.1)

                ele.click()
                logger.debug(f"✅ 点击元素成功：{locator} (第{retry + 1}次尝试)")
                return

            except (ElementClickInterceptedException, ElementNotInteractableException,
                    StaleElementReferenceException, TimeoutException) as e:
                # 这几类异常通常是因为元素还没稳定（比如 React 重新渲染、弹窗遮罩、动画过渡）
                # 重试几次大概率就能点上，不用直接上 JS
                last_exception = e
                if retry < retry_times - 1:
                    logger.warning(f"⚠️ 第{retry + 1}次点击失败，{retry_interval}秒后重试... 错误：{str(e)[:100]}")
                    time.sleep(retry_interval)
                else:
                    logger.warning(f"⚠️ 普通点击全部失败，尝试JS点击... 最后一次错误：{str(e)[:100]}")
                    break

            except Exception as e:
                # 其他异常（比如定位器语法错误）直接抛，重试没有意义
                self._error_record("click", locator, e)
                raise

        # 最后防线：JS 点击
        # 能绕过大部分拦截（遮罩层、pointer-events: none、元素被其他 div 盖住等）
        try:
            wait = WebDriverWait(self.driver, _timeout, self.poll_interval)
            ele = wait.until(EC.element_to_be_clickable(loc))
            self.driver.execute_script("arguments[0].click();", ele)
            logger.debug(f"✅ JS点击元素成功：{locator}")
            return
        except Exception as js_e:
            # 抛原始异常而不是 JS 异常，因为根本问题通常是元素找不到/不可点击
            # JS 异常只是最后一层包装，看原始异常更容易定位问题
            logger.error(f"❌ JS点击也失败：{locator}，错误：{str(js_e)}")
            self._error_record("click", locator, js_e)
            raise last_exception from js_e

    def _error_record(self, action, locator, exception):
        """统一错误记录方法"""
        error_msg = f"执行{action}操作失败，元素：{locator}，错误：{str(exception)}"
        logger.error(error_msg)

    def clear(self, locator, change_data=None):
        """
        通用智能清空（适配React/Vue/Angular + OrangeHRM日期框终极修复）
        """
        ele = self.findElement(locator, change_data)

        # 这套组合拳是专门治前端框架的输入框的
        # 很多框架（React/Vue）不是直接监听 input.value，而是监听 input 事件
        # 所以光 ele.clear() 或者 ele.value = '' 没用，页面显示清空了但框架里的值还在
        # 另外 OrangeHRM 有些日期框加了 readonly，必须先摘掉
        self.driver.execute_script("""
            arguments[0].removeAttribute('readonly');
            arguments[0].removeAttribute('disabled');
            arguments[0].value = '';
            arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
            arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
            arguments[0].dispatchEvent(new Event('blur', { bubbles: true }));
        """, ele)

        # 如果 JS 清空后 value 还不为空，再用原生方式兜底
        # 有些老系统或者非框架页面，JS 赋值反而不会触发后续校验
        if ele.get_attribute('value') != '':
            try:
                ele.click()
                ele.send_keys(Keys.CONTROL + "a")
                ele.send_keys(Keys.DELETE)
            except Exception:
                pass

        # 清空失败直接抛异常，避免后续 sendKeys 拼接到旧内容上
        # 之前踩过坑：清空没生效，输入新内容变成"旧内容+新内容"，导致用例莫名其妙失败
        if ele.get_attribute('value') != '':
            raise Exception(f"智能清空失败：{locator}")

        logger.debug(f"智能清空输入框成功：{locator}")

    def get_text_count(self, text):
        """
        获取页面中指定文本出现的次数
        """
        # 给异步渲染留点时间，特别是表格数据是接口返回的情况
        time.sleep(0.5)
        page_html = self.driver.page_source
        count = page_html.count(text)
        return count

    def sendKeys(self, locator, text="", change_data=None):
        """
        通用输入（集成智能清空，适配所有前端框架）
        """
        try:
            self.clear(locator, change_data)
            ele = self.findElement(locator, change_data)
            ele.send_keys(text)
            logger.debug(f"输入文本成功：{locator} -> {text}")
        except Exception as e:
            logger.error(f"输入文本失败：{locator}")
            raise e

    def get_title(self):
        """获取页面标题"""
        return self.driver.title

    def get_text(self, locator, change_data=None):
        """获取元素文本"""
        return self.findElement(locator, change_data).text

    def get_attribute(self, locator, name, change_data=None):
        """获取元素属性"""
        return self.findElement(locator, change_data).get_attribute(name)

    def isSelected(self, locator, change_data=None):
        """判断元素是否选中"""
        return self.findElement(locator, change_data).is_selected()

    def is_title(self, _title=""):
        """判断标题完全匹配"""
        try:
            return WebDriverWait(self.driver, self.default_timeout, self.poll_interval).until(
                EC.title_is(_title)
            )
        except:
            return False

    def is_title_contains(self, _title=""):
        """判断标题包含"""
        try:
            return WebDriverWait(self.driver, self.default_timeout, self.poll_interval).until(
                EC.title_contains(_title)
            )
        except:
            return False

    def is_text_in_element(self, locator, _text='', change_data=None):
        """判断元素内包含文本"""
        try:
            loc = self.get_locator_data(locator, change_data)
            return WebDriverWait(self.driver, self.default_timeout).until(
                EC.text_to_be_present_in_element(loc, _text)
            )
        except:
            return False

    def is_value_in_element(self, locator, _value='', change_data=None):
        """判断元素value属性包含内容"""
        try:
            loc = self.get_locator_data(locator, change_data)
            return WebDriverWait(self.driver, self.default_timeout).until(
                EC.text_to_be_present_in_element_value(loc, _value)
            )
        except:
            return False

    def is_alert(self, timeout=3):
        """判断alert弹窗是否存在"""
        try:
            return WebDriverWait(self.driver, timeout, self.poll_interval).until(
                EC.alert_is_present()
            )
        except:
            return False

    def mouse_move_to(self, locator, change_data=None):
        """鼠标悬停（通用）"""
        ele = self.findElement(locator, change_data)
        ActionChains(self.driver).move_to_element(ele).perform()

    def mouse_drag_to(self, locator, xoffset, yoffset, change_data=None):
        """鼠标拖拽"""
        ele = self.findElement(locator, change_data)
        # 原代码漏了 .perform()，ActionChains 不调用 perform 是不会执行的
        ActionChains(self.driver).drag_and_drop_by_offset(ele, xoffset, yoffset).perform()
        logger.info(f"元素{locator}拖拽至({xoffset},{yoffset})")

    def js_focus_element(self, locator, change_data=None):
        """滚动到元素可见位置"""
        target = self.findElement(locator, change_data)
        self.driver.execute_script("arguments[0].scrollIntoView(true);", target)

    def js_scroll_end(self, x=0):
        """滚动到页面底部"""
        self.driver.execute_script(f"window.scrollTo({x}, document.body.scrollHeight)")

    def js_scroll_top(self):
        """滚动到页面顶部"""
        self.driver.execute_script("window.scrollTo(0,0)")

    def keyboard_send_keys_to(self, locator, text, change_data=None):
        """键盘输入到指定元素"""
        ele = self.findElement(locator, change_data)
        ActionChains(self.driver).send_keys_to_element(ele, text).perform()

    def get_alert_text(self):
        return self.driver.switch_to.alert.text

    def alert_accept(self):
        self.driver.switch_to.alert.accept()

    def alert_dismiss(self):
        self.driver.switch_to.alert.dismiss()

    def input_alert(self, text):
        self.driver.switch_to.alert.send_keys(text)

    def select_by_index(self, locator, index=0, change_data=None):
        """原生下拉框 - 索引选择"""
        Select(self.findElement(locator, change_data)).select_by_index(index)

    def select_by_value(self, locator, value, change_data=None):
        """原生下拉框 - value选择"""
        Select(self.findElement(locator, change_data)).select_by_value(value)

    def select_by_text(self, locator, text, change_data=None):
        """原生下拉框 - 文本选择"""
        Select(self.findElement(locator, change_data)).select_by_visible_text(text)

    def switch_iframe(self, locator, change_data=None):
        """通用切换iframe（支持索引/名称/元素）"""
        target = self.get_locator_data(locator, change_data)
        # 有些 iframe 是用索引（0,1,2...）或者 name 属性切的，不用每次都先定位元素
        if isinstance(target, (int, str)):
            self.driver.switch_to.frame(target)
        else:
            self.driver.switch_to.frame(self.findElement(locator, change_data))
        logger.info(f"切换iframe成功：{target}")

    def switch_iframe_out(self):
        """切回主文档"""
        self.driver.switch_to.default_content()

    def switch_iframe_up(self):
        """切回父iframe"""
        self.driver.switch_to.parent_frame()

    def get_handles(self):
        return self.driver.window_handles

    def switch_handle(self, index=-1):
        """切换窗口（默认最后一个）"""
        handles = self.driver.window_handles
        self.driver.switch_to.window(handles[index])
        logger.info(f"切换窗口成功：索引{index}")

    def check(self, key_text, timeout=10):
        """稳定通用勾选：适配 复选框在文本左侧 的标准表格"""
        wait = WebDriverWait(self.driver, timeout)
        # 先通过文本找到行，再用 preceding 轴找同行的 checkbox
        # 不要直接点击文本元素，因为文本可能是 span，点击它不会触发勾选
        text_ele = wait.until(
            EC.presence_of_element_located((By.XPATH, f'//*[normalize-space()="{key_text}"]'))
        )
        checkbox = text_ele.find_element(By.XPATH, './/preceding::input[@type="checkbox"][1]')

        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", checkbox)
        time.sleep(0.2)

        if not checkbox.is_selected():
            # OrangeHRM 的事件绑定在 label 上，不是 checkbox 本身
            # 直接点 checkbox 可能能勾选但状态不更新，点 label 才能触发完整逻辑
            label_ele = checkbox.find_element(By.XPATH, './parent::label')
            self.driver.execute_script("arguments[0].click();", label_ele)
            time.sleep(0.5)
            logger.info(f"✅ 勾选成功：{key_text}")

    def check_all(self):
        """一键全选当前页所有可见复选框"""
        from selenium.common.exceptions import ElementNotInteractableException
        WebDriverWait(self.driver, 5).until(
            EC.presence_of_all_elements_located((By.XPATH, "//input[@type='checkbox']"))
        )
        checkboxes = self.driver.find_elements(By.XPATH, "//input[@type='checkbox']")
        for box in checkboxes:
            try:
                if box.is_displayed() and not box.is_selected():
                    self.driver.execute_script("arguments[0].click();", box)
            except ElementNotInteractableException:
                # 表格里有些 checkbox 是表头的或者隐藏的，点不到就跳过
                continue

    def wait_for_toast(self, text: str, timeout: float = 2, interval: float = 0.05) -> bool:
        """这个方法只适用于otd
        激进等待 Toast：每隔 interval 秒检查一次 DOM 中是否存在包含文本的 .oxd-toast 元素。
        只要出现一次就返回 True。
        """
        # 注意：这个方法是 OrangeHRM 专属的，别的系统 toast 类名不一样
        # 2 秒超时 + 0.05 秒轮询比较激进，因为 toast 通常显示 3-5 秒就消失了，等太久容易错过
        logger.debug(f"⏳ 等待Toast包含文本：{text}，超时={timeout}s")
        start = time.time()
        while time.time() - start < timeout:
            toasts = self.driver.find_elements(By.XPATH, "//div[contains(@class,'oxd-toast')]")
            for toast in toasts:
                if text in toast.text:
                    logger.debug(f"✅ 找到Toast：{text}")
                    return True
            time.sleep(interval)

        logger.debug(f"❌ 未找到Toast：{text}")
        return False

    def handle_confirm_modal(self,
                             action: str = "confirm",
                             custom_confirm_text: str = None,
                             custom_cancel_text: str = None,
                             custom_modal_locator: tuple = None,
                             timeout: int = 10) -> bool:
        """
        终极智能通用确认弹窗处理方法（企业级标准）
        """
        # 内置了主流前端框架的弹窗特征，开箱即用
        # 实际项目中弹窗五花八门，这里把常见套路都枚举了，省得每个系统都重写
        COMMON_MODAL_LOCATORS = [
            (By.XPATH, '//div[contains(@class, "oxd-dialog-container")]'),  # OrangeHRM
            (By.XPATH, '//div[contains(@class, "el-dialog")]'),  # ElementUI
            (By.XPATH, '//div[contains(@class, "ant-modal")]'),  # Ant Design
            (By.XPATH, '//div[contains(@class, "modal-dialog")]'),  # Bootstrap
            (By.XPATH, '//div[contains(@class, "v-dialog")]'),  # Vuetify
            (By.XPATH, '//div[@role="dialog"]'),  # 通用标准
        ]

        COMMON_CONFIRM_TEXTS = [
            "Yes, Delete", "Yes", "Delete", "Confirm", "OK", "确定", "确认", "删除", "提交", "保存"
        ]

        COMMON_CANCEL_TEXTS = [
            "Cancel", "No", "Close", "取消", "关闭", "返回"
        ]

        try:
            logger.info(f"🔍 智能处理确认弹窗，操作：{action}")

            # 先判断是不是原生 alert，这个优先级最高
            # 因为原生 alert 会阻塞页面，如果不先处理，后面的元素定位都会卡死
            try:
                alert = self.driver.switch_to.alert
                logger.debug("✅ 检测到原生JS弹窗")
                if action.lower() == "confirm":
                    alert.accept()
                else:
                    alert.dismiss()
                logger.info("✅ 原生JS弹窗处理完成")
                return True
            except NoAlertPresentException:
                logger.debug("ℹ️ 未检测到原生JS弹窗，开始查找自定义模态框")

            modal = None
            if custom_modal_locator:
                modal = WebDriverWait(self.driver, timeout).until(
                    EC.visibility_of_element_located(custom_modal_locator)
                )
            else:
                # 遍历所有已知框架的弹窗容器，哪个先出现就用哪个
                for locator in COMMON_MODAL_LOCATORS:
                    try:
                        modal = WebDriverWait(self.driver, 2).until(
                            EC.visibility_of_element_located(locator)
                        )
                        logger.debug(f"✅ 自动识别到弹窗：{locator}")
                        break
                    except TimeoutException:
                        continue

                if not modal:
                    raise TimeoutException("未找到任何已知类型的弹窗")

            # 弹窗通常有淡入动画，立即点击可能点不到
            time.sleep(0.8)

            btn = None
            if action.lower() == "confirm":
                if custom_confirm_text:
                    btn = modal.find_element(By.XPATH, f'.//button[contains(., "{custom_confirm_text}")]')
                else:
                    # 遍历常见确认按钮文本，多语言、多系统都能覆盖
                    for text in COMMON_CONFIRM_TEXTS:
                        try:
                            btn = modal.find_element(By.XPATH, f'.//button[contains(., "{text}")]')
                            logger.debug(f"✅ 自动识别到确认按钮：{text}")
                            break
                        except NoSuchElementException:
                            continue
            elif action.lower() == "cancel":
                if custom_cancel_text:
                    btn = modal.find_element(By.XPATH, f'.//button[contains(., "{custom_cancel_text}")]')
                else:
                    for text in COMMON_CANCEL_TEXTS:
                        try:
                            btn = modal.find_element(By.XPATH, f'.//button[contains(., "{text}")]')
                            logger.debug(f"✅ 自动识别到取消按钮：{text}")
                            break
                        except NoSuchElementException:
                            continue
            else:
                logger.error(f"❌ 不支持的操作类型：{action}，仅支持 confirm/cancel")
                return False

            if not btn:
                raise NoSuchElementException(f"未找到{action}按钮，已遍历所有内置文本")

            # 很多弹窗有遮罩层（backdrop）或者按钮被 pointer-events 挡住，普通 click 点不上
            # JS 点击能绕过绝大部分这类拦截
            self.driver.execute_script("arguments[0].click();", btn)
            logger.info(f"✅ 点击按钮成功")

            # 点击后等弹窗消失，防止后续操作撞到还没完全退场的弹窗
            WebDriverWait(self.driver, timeout).until(
                EC.invisibility_of_element_located(modal)
            )
            logger.info("✅ 弹窗已关闭，操作完成")

            return True

        except TimeoutException as e:
            logger.error(f"❌ 弹窗处理超时：{str(e)}")
            return False
        except NoSuchElementException as e:
            logger.error(f"❌ 元素未找到：{str(e)}")
            return False
        except Exception as e:
            logger.error(f"❌ 弹窗处理异常：{str(e)}")
            return False

    def scroll_to_element(self, locator, change_data=None):
        """
        最终修复版：动态元素必找到，滚动必执行
        专门适配：勾选后才出现的 Records Selected 元素
        """
        try:
            # 动态元素（比如勾选后才出现的批量操作栏）需要等它进 DOM
            # 用 presence 而不是 visibility，因为有些元素刚出现时可能是隐藏的
            wait = WebDriverWait(self.driver, 10)
            loc = self.get_locator_data(locator, change_data)
            ele = wait.until(EC.presence_of_element_located(loc))

            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", ele)
            time.sleep(0.5)
            logger.info(f"✅ 滚动成功：{locator}")

        except Exception as e:
            logger.error(f"❌ 滚动失败：{str(e)}")

    def select_dropdown(self, yaml_key: str, target: str, timeout: int = 7) -> bool:
        """
        真正通用下拉选择方法（适配所有类型）
        """
        try:
            logger.info(f"🔍 通用下拉选择：{target}")
            locator = self.get_locator_data(yaml_key)

            # poll_frequency 从默认 0.5 改成 0.2，响应更快
            # 下拉选项通常出现得很快，0.5 秒轮询有点浪费等待时间
            wait = WebDriverWait(self.driver, timeout, poll_frequency=0.2)
            dropdown = wait.until(EC.element_to_be_clickable(locator))

            if dropdown.tag_name.lower() == "select":
                # 原生 select 标签直接用 Selenium 的 Select 类，最稳定
                Select(dropdown).select_by_visible_text(target)
                logger.info("✅ 原生select下拉选择成功")
                return True

            elif "oxd-select-wrapper" in dropdown.get_attribute("class"):
                # OrangeHRM 的 OXD 下拉是自定义组件，不是原生 select
                # 需要先点击展开，再选选项，而且选项是动态插入 DOM 的
                self.driver.execute_script("arguments[0].click();", dropdown)
                time.sleep(0.6)
                option_xpath = f'//div[@class="oxd-select-option"]/span[text()="{target}"]'
                option = wait.until(EC.element_to_be_clickable((By.XPATH, option_xpath)))
                self.driver.execute_script("arguments[0].click();", option)
                logger.info("✅ OrangeHRM OXD下拉选择成功")
                return True

            else:
                # 通用自定义下拉：先点击展开，再尝试几种常见的选项定位方式
                dropdown.click()
                time.sleep(0.5)
                option_locators = [
                    (By.XPATH, f'//div[text()="{target}"]'),
                    (By.XPATH, f'//span[text()="{target}"]'),
                    (By.XPATH, f'//li[text()="{target}"]')
                ]
                for loc in option_locators:
                    try:
                        option = WebDriverWait(self.driver, 3, poll_frequency=0.2).until(
                            EC.element_to_be_clickable(loc)
                        )
                        option.click()
                        logger.info("✅ 通用自定义下拉选择成功")
                        return True
                    except:
                        continue
                raise Exception("未找到匹配的选项")

        except Exception as e:
            logger.error(f"❌ 下拉选择失败：{str(e)}")
            return False

    def select_top_nav_drop(self, yaml_key: str, target_text: str, timeout: int = 10) -> bool:
        """
        通用顶部导航下拉选择：展开菜单并精准选中指定项
        兼容 OXD / ElementUI / AntD / 普通 CSS 下拉，不依赖固定类名
        """
        try:
            logger.info(f"🔍 顶部下拉选择：{target_text}")
            wait = WebDriverWait(self.driver, timeout, poll_frequency=self.poll_interval)

            btn_locator = self.get_locator_data(yaml_key)
            btn = wait.until(EC.element_to_be_clickable(btn_locator))
            self.driver.execute_script("arguments[0].click();", btn)

            # 顶部导航的下拉面板类名各家不一样，这里枚举常见的
            container_locators = [
                (By.XPATH, "//ul[contains(@class,'dropdown-menu')]"),
                (By.XPATH, "//div[contains(@class,'oxd-dropdown')]"),
                (By.XPATH, "//div[contains(@class,'el-dropdown-menu')]"),
                (By.XPATH, "//div[contains(@class,'ant-dropdown')]"),
                (By.XPATH, "//ul[@role='menu']"),
                (By.XPATH, "//div[@role='menu']"),
            ]
            container = None
            for loc in container_locators:
                try:
                    container = WebDriverWait(self.driver, 3, poll_frequency=self.poll_interval).until(
                        EC.visibility_of_element_located(loc)
                    )
                    break
                except TimeoutException:
                    continue

            # 如果没匹配到标准容器，降级为全局查找
            # 但全局查找容易误触，所以加了 class/role 限制，尽量缩小范围
            if container is None:
                logger.warning("未找到标准下拉容器，将使用全局查找（可能误触）")
                option_xpath = (
                    f"//*[contains(@class,'dropdown-item') and normalize-space()='{target_text}'] | "
                    f"//*[@role='menuitem' and normalize-space()='{target_text}'] | "
                    f"//li[normalize-space()='{target_text}'] | "
                    f"//span[normalize-space()='{target_text}'] | "
                    f"//div[normalize-space()='{target_text}']"
                )
                option = WebDriverWait(self.driver, timeout, poll_frequency=self.poll_interval).until(
                    EC.element_to_be_clickable((By.XPATH, option_xpath))
                )
            else:
                # 在容器内部查找，比全局查找精准得多
                option_xpath = (
                    f".//*[normalize-space()='{target_text}'] | "
                    f".//*[contains(normalize-space(), '{target_text}')]"
                )
                option = WebDriverWait(self.driver, timeout, poll_frequency=self.poll_interval).until(
                    lambda d: container.find_element(By.XPATH, option_xpath)
                )
                WebDriverWait(self.driver, 3).until(EC.element_to_be_clickable(option))

            self.driver.execute_script("arguments[0].click();", option)
            logger.info(f"✅ 顶部导航选中：{target_text}")
            return True

        except Exception as e:
            logger.error(f"❌ 顶部下拉失败：{str(e)}")
            return False

    def get_selected_value(self, yaml_key: str, timeout: int = 10) -> str:
        """
        适配OrangeHRM + 通用系统，选择后100%拿到选中值
        """
        try:
            locator = self.get_locator_data(yaml_key)
            WebDriverWait(self.driver, timeout).until(EC.visibility_of_element_located(locator))

            # OrangeHRM 的下拉选中值不在 select 的 value 里，而是在 oxd-select-text-input 的 text 里
            # 这个类名是 OrangeHRM 特有的，别的系统可能不适用
            value = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CLASS_NAME, "oxd-select-text-input"))
            ).text.strip()

            logger.info(f"✅ 成功获取下拉选中值：{value}")
            return value

        except Exception as e:
            logger.error(f"❌ 获取选中值失败：{str(e)}")
            return ""

    def set_input_value(self, yaml_key: str, value: str, trigger_events: bool = True, timeout: int = 10):
        """
        企业级通用输入框赋值方法
        适配所有现代前端框架（React/Vue/Angular），解决所有输入失效问题
        """
        try:
            ele = self.findElement(yaml_key, timeout=timeout)

            # 有些输入框加了 readonly 或者 disabled，不先解除的话，JS 赋值也写不进去
            self.driver.execute_script("""
                arguments[0].removeAttribute('readonly');
                arguments[0].removeAttribute('disabled');
                arguments[0].removeAttribute('aria-readonly');
                arguments[0].removeAttribute('aria-disabled');
            """, ele)

            self.driver.execute_script("arguments[0].value = '';", ele)
            self.driver.execute_script("arguments[0].value = arguments[1];", ele, value)

            if trigger_events:
                # 前端框架通常监听 input / change / blur 等事件
                # 但有些框架（比如 React）还有合成事件系统，所以多触发几个，宁可错杀不可放过
                self.driver.execute_script("""
                    const events = [
                        'input', 'change', 'blur', 'focusout', 'keyup', 'keydown', 'keypress',
                        'paste', 'cut', 'compositionend', 'react-input', 'react-change'
                    ];
                    events.forEach(eventName => {
                        const event = new Event(eventName, { bubbles: true, cancelable: true });
                        arguments[0].dispatchEvent(event);
                    });
                """, ele)

            # 如果 JS 赋值后 value 还是不对，降级用原生 send_keys
            # 有些系统对 JS 赋值有校验，必须用真实键盘输入才能通过
            if ele.get_attribute('value') != value:
                ele.click()
                ele.send_keys(Keys.CONTROL + "a")
                ele.send_keys(value)

            time.sleep(0.2)
            logger.debug(f"✅ 通用输入框赋值成功：{yaml_key} = {value}")

        except Exception as e:
            logger.error(f"❌ 通用输入框赋值失败：{yaml_key} = {value}，错误：{str(e)}")
            raise

    def select_search_drop(self, input_loc, target_text, panel_xpath=None):
        """
        【全系统通用】搜索联想自动补全下拉
        适配：OrangeHRM/ElementUI/AntD/自研系统等所有Web联想框
        """
        input_ele = self.findElement(input_loc)
        input_ele.click()
        input_ele.clear()
        input_ele.send_keys(target_text)
        time.sleep(2)

        # 联想下拉面板通常有 role='option' 或者带 dropdown/select 类名
        # 如果某个系统比较特殊，可以通过 panel_xpath 自定义
        default_panel = "//*[@role='option' or contains(@class,'dropdown') or contains(@class,'select')]"
        final_xpath = panel_xpath if panel_xpath else default_panel

        option_ele = WebDriverWait(self.driver, self.default_timeout, self.poll_interval).until(
            EC.element_to_be_clickable((By.XPATH, final_xpath))
        )
        option_ele.click()
        logger.info("✅ 通用联想下拉选择完成")

if __name__ == '__main__':
    web  = WebBase("Web元素信息-登录")
    res = web.get_locator_data("login/loginbtn")
    print(res)