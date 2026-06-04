"""
@Author  : 谢胜强
@Time    : 2026/5/16 21:42
@Desc    : 桌面客户端GUI自动化通用基类
            适配所有Windows客户端，基于pyautogui/pyperclip封装
"""
import os
import time
from typing import Optional, Tuple, List

import pyautogui
import pyperclip

from Base.baseData import DataBase
from Base.baseLogger import Logger
from Base.basePath import BasePath as BP

logger = Logger('baseAutoClient.py').getLogger()

# 全局初始化：自动创建截图目录（避免报错）
os.makedirs(BP.SCREENSHOT_DIR, exist_ok=True)


class GuiBase(DataBase):
    """桌面客户端GUI自动化通用基类（全平台通用）"""

    def __init__(self) -> None:
        super().__init__()
        client_config = self.config['客户端自动化配置']

        # 配置项比较多，这里校验写得有点啰嗦，但能提前发现问题
        # 之前遇到过 confidence 配成 1.2 导致 locateOnScreen 直接抛异常的情况
        # 与其在运行时莫名其妙报错，不如初始化时就掐死
        try:
            self.duration = float(client_config['duration'])
            self.interval = float(client_config['interval'])
            self.timeout = float(client_config['minSearchTime'])
            self.confidence = float(client_config['confidence'])
            self.grayscale = bool(client_config['grayscale'])
            # 新增：点击失败重试次数配置（默认1次）
            self.click_retry_count = int(client_config.get('clickRetryCount', 1))
            # 新增：操作后默认等待时间（可配置）
            self.operation_delay = float(client_config.get('operationDelay', 0.1))

            if self.duration < 0:
                raise ValueError("duration不能为负数")
            if self.interval < 0:
                raise ValueError("interval不能为负数")
            if self.timeout < 0:
                raise ValueError("timeout不能为负数")
            if not (0 < self.confidence <= 1):
                raise ValueError("confidence必须在(0, 1]范围内")
            if self.click_retry_count < 0:
                raise ValueError("clickRetryCount不能为负数")
            if self.operation_delay < 0:
                raise ValueError("operationDelay不能为负数")
        except (KeyError, ValueError) as e:
            logger.error(f"❌ 客户端自动化配置错误：{e}")
            raise

        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.1

    # ─────────────────── 内部工具方法 ───────────────────
    def _is_file_exist(self, el: str) -> str:
        """校验图片资源是否存在，返回绝对路径"""
        abs_path = self.api_path.get(el)
        if not abs_path or not os.path.exists(abs_path):
            # 错误信息里带上实际查找路径，省得再去翻配置猜路径
            raise FileNotFoundError(f"图片元素【{el}】不存在，查找路径：{abs_path}")
        return abs_path

    def _error_record(self, name: str, func_type: str) -> None:
        """统一异常处理 + 自动截图"""
        # 截图文件名带上元素名和 timestamp，方便一眼看出是哪一步挂了
        # 之前截图都叫 error.png，跑完一堆用例根本不知道哪张是哪张
        screenshot_name = f"{func_type}_{name}_{int(time.time())}.png"
        screenshot_path = os.path.join(BP.SCREENSHOT_DIR, screenshot_name)

        # 截图本身也可能失败（比如权限问题），别让截图异常把原始错误吞了
        try:
            pyautogui.screenshot(screenshot_path)
            logger.error(f"❌ 【{func_type}】查找图片【{name}】失败，已截图：{screenshot_path}")
        except Exception as e:
            logger.error(f"❌ 【{func_type}】查找图片【{name}】失败，截图失败：{e}")

        raise pyautogui.ImageNotFoundException(f"图片【{name}】未找到")

    # ─────────────────── 图片定位 ───────────────────
    def isexist(self, el: str, timeout: Optional[float] = None) -> Optional[pyautogui.Point]:
        """检查图片是否在屏幕中，存在返回中心坐标，不存在返回None"""
        pic_path = self._is_file_exist(el)
        # 显式区分 timeout=0 与未传参的情况
        # 因为 timeout=0 在 pyautogui 里是有意义的（立即返回），不能当成默认超时处理
        wait_time = timeout if timeout is not None else self.timeout

        try:
            coordinates = pyautogui.locateOnScreen(
                pic_path,
                timeout=wait_time,
                confidence=self.confidence,
                grayscale=self.grayscale
            )
            if coordinates:
                center_pos = pyautogui.center(coordinates)
                logger.debug(f"✅ 查找图片【{el}】成功，坐标：{center_pos}")
                return center_pos

            logger.debug(f"❌ 查找图片【{el}】失败")
            return None
        except Exception as e:
            logger.debug(f"❌ 查找图片【{el}】时发生异常：{e}")
            return None

    # ─────────────────── 鼠标操作 ───────────────────
    def click_picture(self, el: str, clicks: int = 1, button: str = 'left',
                      isclick: bool = True) -> None:
        """图片定位点击（核心方法）"""
        # 加了个重试机制，因为客户端有时候加载慢，第一次 locate 失败但第二次就找到了
        # 重试次数配在配置文件里，默认只重试1次，够用又不至于拖太久
        for retry in range(self.click_retry_count + 1):
            pos = self.isexist(el)
            if pos:
                break
            if retry < self.click_retry_count:
                logger.debug(f"⏳ 第{retry + 1}次点击【{el}】失败，重试中...")
                time.sleep(0.5)
        else:
            self._error_record(el, 'click_picture')

        pyautogui.moveTo(*pos, duration=self.duration)
        if isclick:
            # 先 moveTo 再 click，避免 pyautogui 在点击前瞬间重新定位导致点歪
            pyautogui.click(clicks=clicks, button=button, interval=self.interval)
            time.sleep(self.operation_delay)
            logger.info(f"✅ 点击图片【{el}】成功，坐标：{pos}")
        else:
            logger.info(f"✅ 移动到图片【{el}】成功，坐标：{pos}")

    def rel_click_picture(self, el: str, rel_x: int = 0, rel_y: int = 0,
                          clicks: int = 1, button: str = 'left', isclick: bool = True) -> None:
        """图片相对位置点击"""
        # 同样加了重试，逻辑和 click_picture 保持一致
        for retry in range(self.click_retry_count + 1):
            pos = self.isexist(el)
            if pos:
                break
            if retry < self.click_retry_count:
                logger.debug(f"⏳ 第{retry + 1}次相对点击【{el}】失败，重试中...")
                time.sleep(0.5)
        else:
            self._error_record(el, 'rel_click_picture')

        pyautogui.moveTo(*pos, duration=self.duration)
        pyautogui.moveRel(rel_x, rel_y, duration=self.duration)
        if isclick:
            pyautogui.click(clicks=clicks, button=button, interval=self.interval)
            time.sleep(self.operation_delay)
            logger.info(f"✅ 相对点击【{el}】偏移({rel_x},{rel_y})成功")
        else:
            logger.info(f"✅ 相对移动【{el}】偏移({rel_x},{rel_y})成功")

    def click(self, posx: Optional[int] = None, posy: Optional[int] = None,
              clicks: int = 1, button: str = 'left') -> None:
        """鼠标绝对位置点击"""
        # 坐标为负数大概率是传错了，给个警告但不拦死
        # 因为多屏环境下负数坐标可能是合法的（副屏在主屏左边）
        if posx is not None and posx < 0:
            logger.warning(f"⚠️ 点击坐标x={posx}为负数，可能超出屏幕范围")
        if posy is not None and posy < 0:
            logger.warning(f"⚠️ 点击坐标y={posy}为负数，可能超出屏幕范围")
        if clicks < 1:
            logger.warning("⚠️ 点击次数clicks<<1，操作被忽略")
            return

        pyautogui.click(posx, posy, clicks=clicks, button=button,
                        duration=self.duration, interval=self.interval)
        time.sleep(self.operation_delay)
        logger.info(f"✅ 绝对点击坐标：({posx}, {posy})")

    def rel_click(self, rel_x: int = 0, rel_y: int = 0,
                  clicks: int = 1, button: str = 'left') -> None:
        """鼠标相对位置点击"""
        if clicks < 1:
            logger.warning("⚠️ 点击次数clicks<<1，操作被忽略")
            return

        pyautogui.moveRel(rel_x, rel_y, duration=self.duration)
        pyautogui.click(clicks=clicks, button=button, interval=self.interval)
        time.sleep(self.operation_delay)
        logger.info(f"✅ 相对点击偏移({rel_x},{rel_y})成功")

    def moveto(self, posx: int, posy: int, rel: bool = False) -> None:
        """鼠标移动（绝对/相对）"""
        if not rel and (posx < 0 or posy < 0):
            logger.warning(f"⚠️ 移动坐标({posx},{posy})为负数，可能超出屏幕范围")

        if rel:
            pyautogui.moveRel(posx, posy, duration=self.duration)
            logger.info(f"✅ 鼠标偏移至({posx},{posy})")
        else:
            pyautogui.moveTo(posx, posy, duration=self.duration)
            logger.info(f"✅ 鼠标移动至({posx},{posy})")

    def dragto(self, posx: int, posy: int, button: str = 'left', rel: bool = False) -> None:
        """鼠标拖拽（绝对/相对）"""
        if not rel and (posx < 0 or posy < 0):
            logger.warning(f"⚠️ 拖拽目标坐标({posx},{posy})为负数，可能超出屏幕范围")

        if rel:
            pyautogui.dragRel(posx, posy, button=button, duration=self.duration)
            logger.info(f"✅ 相对拖拽至({posx},{posy})")
        else:
            pyautogui.dragTo(posx, posy, button=button, duration=self.duration)
            logger.info(f"✅ 绝对拖拽至({posx},{posy})")
        time.sleep(self.operation_delay)

    def scroll(self, amount_to_scroll: int,
               moveToX: Optional[int] = None, moveToY: Optional[int] = None) -> None:
        """鼠标滚轮滚动"""
        if amount_to_scroll == 0:
            logger.warning("⚠️ 滚动值为0，操作被忽略")
            return

        pyautogui.scroll(clicks=amount_to_scroll, x=moveToX, y=moveToY)
        logger.info(f"✅ 鼠标在({moveToX},{moveToY})滚动值：{amount_to_scroll}")

    # ─────────────────── 键盘操作 ───────────────────
    def type(self, *args: str) -> None:
        """英文输入（不支持中文）"""
        if not args:
            logger.warning("⚠️ 输入内容为空，操作被忽略")
            return

        pyautogui.write(*args, interval=self.interval)
        logger.info(f"✅ 输入英文内容：{args}")

    def input_string(self, text: str, clear: bool = False) -> None:
        """通用中文输入（支持先清空）"""
        if text is None:
            logger.warning("⚠️ 输入文本为None，操作被忽略")
            return

        if clear:
            # 优先用 ctrl+a + backspace 清空，比连续按 50 次 backspace 靠谱
            # 但有些控件（比如某些自定义输入框）不支持 ctrl+a，所以留了备用方案
            try:
                pyautogui.hotkey('ctrl', 'a')
                time.sleep(0.05)
                pyautogui.press('backspace')
                time.sleep(0.05)
            except Exception:
                logger.debug("⚠️ ctrl+a清空失败，使用备用方案")
                pyautogui.press('backspace', presses=50, interval=0.01)

        # 用 pyperclip 处理中文输入是无奈之举
        # pyautogui.typewrite 对中文支持很差，直接乱码
        # 注意：这会覆盖剪贴板原有内容，如果后续需要粘贴别的内容，记得重新 copy
        pyperclip.copy(text)
        time.sleep(0.05)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(self.operation_delay)
        logger.info(f"✅ 输入中文内容：{text}")

    def press(self, key: str) -> None:
        """单个键盘按键"""
        if not key:
            logger.warning("⚠️ 按键为空，操作被忽略")
            return

        pyautogui.press(key, interval=self.interval)
        logger.info(f"✅ 按下按键：{key}")

    def hotkey(self, *keys: str) -> None:
        """键盘组合快捷键"""
        if not keys:
            logger.warning("⚠️ 快捷键为空，操作被忽略")
            return

        pyautogui.hotkey(*keys, interval=self.interval)
        logger.info(f"✅ 执行快捷键：{'+'.join(keys)}")

    # ─────────────────── 扩展方法 ───────────────────
    def wait_for_appear(self, el: str, timeout: Optional[float] = None) -> Optional[pyautogui.Point]:
        """等待图片出现"""
        logger.debug(f"⏳ 等待图片【{el}】出现，超时时间：{timeout or self.timeout}秒")
        result = self.isexist(el, timeout)
        if result:
            logger.debug(f"✅ 图片【{el}】已出现")
        else:
            logger.debug(f"❌ 等待图片【{el}】出现超时")
        return result

    def wait_for_disappear(self, el: str, timeout: Optional[float] = None) -> bool:
        """等待图片消失"""
        pic_path = self._is_file_exist(el)
        wait_time = timeout if timeout is not None else self.timeout
        start_time = time.time()

        logger.debug(f"⏳ 等待图片【{el}】消失，超时时间：{wait_time}秒")

        # 指数退避不是炫技，locateOnScreen 本身就是 CPU 密集型操作
        # 之前固定 0.1 秒轮询，跑久了 CPU 风扇狂转，现在逐渐放宽检查间隔
        check_interval = 0.1
        while time.time() - start_time < wait_time:
            coordinates = pyautogui.locateOnScreen(
                pic_path,
                confidence=self.confidence,
                grayscale=self.grayscale
            )
            if not coordinates:
                logger.debug(f"✅ 图片【{el}】已消失")
                return True
            time.sleep(check_interval)
            check_interval = min(check_interval * 1.2, 0.5)

        logger.error(f"❌ 等待图片【{el}】消失超时，仍存在于屏幕")
        return False

    def find_all(self, el: str) -> List[pyautogui.Point]:
        """查找屏幕上所有匹配的图片位置"""
        pic_path = self._is_file_exist(el)
        logger.debug(f"🔍 查找屏幕上所有【{el}】图片")

        # locateAllOnScreen 返回的是生成器，必须显式转列表，否则只能遍历一次
        all_boxes = list(pyautogui.locateAllOnScreen(
            pic_path,
            confidence=self.confidence,
            grayscale=self.grayscale
        ))
        result = [pyautogui.center(box) for box in all_boxes]

        if result:
            logger.debug(f"✅ 找到【{len(result)}】个【{el}】图片，坐标：{result}")
        else:
            logger.debug(f"❌ 未找到任何【{el}】图片")
        return result

    def screenshot_region(self, x: int, y: int, width: int, height: int,
                          filename: Optional[str] = None) -> str:
        """截取指定区域的屏幕"""
        if x < 0 or y < 0:
            logger.warning(f"⚠️ 截图区域坐标({x},{y})为负数，可能超出屏幕范围")
        if width <= 0 or height <= 0:
            logger.error(f"❌ 截图区域宽高必须大于0，当前：width={width}, height={height}")
            raise ValueError("截图区域宽高必须大于0")

        if not filename:
            filename = f"screenshot_region_{int(time.time())}.png"

        screenshot_path = os.path.join(BP.SCREENSHOT_DIR, filename)
        try:
            pyautogui.screenshot(screenshot_path, region=(x, y, width, height))
            logger.info(f"✅ 区域截图成功，保存至：{screenshot_path}")
            return screenshot_path
        except Exception as e:
            logger.error(f"❌ 区域截图失败：{e}")
            raise

    def get_mouse_position(self) -> Tuple[int, int]:
        """获取鼠标当前位置"""
        pos = pyautogui.position()
        logger.debug(f"🖱️ 鼠标当前位置：({pos.x}, {pos.y})")
        return (pos.x, pos.y)

    def get_screen_size(self) -> Tuple[int, int]:
        """获取屏幕分辨率"""
        size = pyautogui.size()
        logger.debug(f"🖥️ 屏幕分辨率：{size.width}x{size.height}")
        return (size.width, size.height)

    def double_click_picture(self, el: str, button: str = 'left') -> None:
        """图片定位双击（快捷方法）"""
        self.click_picture(el, clicks=2, button=button)
        logger.info(f"✅ 双击图片【{el}】成功")

    def right_click_picture(self, el: str) -> None:
        """图片定位右键点击（快捷方法）"""
        self.click_picture(el, button='right')
        logger.info(f"✅ 右键点击图片【{el}】成功")

    def drag_picture_to_picture(self, el1: str, el2: str,
                                rel_x1: int = 0, rel_y1: int = 0,
                                rel_x2: int = 0, rel_y2: int = 0,
                                button: str = 'left') -> None:
        """从一个图片拖拽到另一个图片"""
        # 源和目标都要查，而且各自独立重试
        # 之前写成分开两次调用 isexist，结果第二次查找时第一个元素可能已经移出屏幕了
        # 所以这里先一次性把两个坐标都拿到，再执行拖拽
        for retry in range(self.click_retry_count + 1):
            source_pos = self.isexist(el1)
            if source_pos:
                break
            if retry < self.click_retry_count:
                logger.debug(f"⏳ 第{retry + 1}次查找源图片【{el1}】失败，重试中...")
                time.sleep(0.5)
        else:
            self._error_record(el1, 'drag_picture_to_picture_source')

        for retry in range(self.click_retry_count + 1):
            target_pos = self.isexist(el2)
            if target_pos:
                break
            if retry < self.click_retry_count:
                logger.debug(f"⏳ 第{retry + 1}次查找目标图片【{el2}】失败，重试中...")
                time.sleep(0.5)
        else:
            self._error_record(el2, 'drag_picture_to_picture_target')

        start_x = source_pos.x + rel_x1
        start_y = source_pos.y + rel_y1
        end_x = target_pos.x + rel_x2
        end_y = target_pos.y + rel_y2

        pyautogui.moveTo(start_x, start_y, duration=self.duration)
        pyautogui.dragTo(end_x, end_y, duration=self.duration, button=button)
        time.sleep(self.operation_delay)
        logger.info(f"✅ 从【{el1}】({start_x},{start_y})拖拽到【{el2}】({end_x},{end_y})成功")

    def get_pixel_color(self, x: int, y: int) -> Tuple[int, int, int]:
        """获取指定坐标的像素颜色"""
        screen_width, screen_height = pyautogui.size()
        if x < 0 or x >= screen_width or y < 0 or y >= screen_height:
            logger.warning(f"⚠️ 像素坐标({x},{y})超出屏幕范围({screen_width}x{screen_height})")

        color = pyautogui.pixel(x, y)
        logger.debug(f"🎨 坐标({x},{y})的像素颜色：RGB{color}")
        return color

    def verify_pixel_color(self, x: int, y: int, expected_color: Tuple[int, int, int],
                           tolerance: int = 10) -> bool:
        """验证像素颜色是否符合预期（带容差）"""
        if len(expected_color) != 3:
            logger.error("❌ 预期颜色必须是包含3个值的RGB元组")
            raise ValueError("预期颜色必须是包含3个值的RGB元组")

        if tolerance < 0 or tolerance > 255:
            logger.warning(f"⚠️ 颜色容差{tolerance}超出合理范围(0-255)，已重置为10")
            tolerance = 10

        actual_color = self.get_pixel_color(x, y)

        diffs = [abs(a - b) for a, b in zip(actual_color, expected_color)]
        if all(d <= tolerance for d in diffs):
            logger.debug(
                f"✅ 坐标({x},{y})颜色验证通过，实际：RGB{actual_color}，预期：RGB{expected_color}，各通道差异：{diffs}")
            return True
        else:
            logger.warning(
                f"❌ 坐标({x},{y})颜色验证失败，实际：RGB{actual_color}，预期：RGB{expected_color}，各通道差异：{diffs}")
            return False

    def scroll_until_appear(self, el: str, scroll_amount: int = -100,
                            max_scrolls: int = 10, direction: str = 'down') -> Optional[pyautogui.Point]:
        """滚动屏幕直到图片出现"""
        pic_path = self._is_file_exist(el)

        # 统一处理方向，避免调用方传错正负号
        # 很多人搞不清楚 scroll 的负数是向上还是向下，这里直接内部消化掉
        direction = direction.lower()
        if direction == 'down':
            scroll_amount = -abs(scroll_amount)
        elif direction == 'up':
            scroll_amount = abs(scroll_amount)
        else:
            logger.warning(f"⚠️ 无效的滚动方向【{direction}】，已默认使用向下滚动")
            scroll_amount = -abs(scroll_amount)

        logger.debug(f"🔄 开始{direction}滚动查找【{el}】，每次滚动{abs(scroll_amount)}像素，最多{max_scrolls}次")

        for i in range(max_scrolls):
            coordinates = pyautogui.locateOnScreen(
                pic_path,
                confidence=self.confidence,
                grayscale=self.grayscale
            )
            if coordinates:
                center_pos = pyautogui.center(coordinates)
                logger.debug(f"✅ 第{i + 1}次滚动后找到【{el}】，坐标：{center_pos}")
                return center_pos

            pyautogui.scroll(scroll_amount)
            time.sleep(self.operation_delay)
            logger.debug(f"⏳ 第{i + 1}次滚动完成，继续查找")

        logger.error(f"❌ 滚动{max_scrolls}次后仍未找到【{el}】")
        return None


if __name__ == '__main__':
    gui = GuiBase()
    time.sleep(2)
    gui.hotkey('win', 'm')  # 最小化所有窗口