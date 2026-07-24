"""
OpenCV 颜色+形状联合识别 (PC端模拟 K230)
==========================================
6颜色(红/绿/蓝/黄/紫/黑) × 3形状(矩形/圆形/三角形)
通过 DETECT 字典指定要检测的颜色+形状组合

用法:
  1. 改下面的 DETECT 字典, 选择要检测的组合
  2. python cv_color_shape.py

按键:
  q / ESC - 退出
  s       - 截图保存为 snapshot.jpg
  ★ 在终端窗口敲 q/s 即可, 不需要点画面窗口 ★
"""

import cv2
import numpy as np
import sys

try:
    import serial
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False
    print("串口功能禁用。")


# ============================================================
# 串口配置 (发给 STM32)
# ============================================================
COM_PORT = 'COM3'           # 改成你电脑上的串口号
BAUDRATE = 115200           # 与 STM32 保持一致
USE_UART = False            # True=启用串口  False=仅打印

if USE_UART and HAS_SERIAL:
    try:
        uart = serial.Serial(COM_PORT, BAUDRATE, timeout=0.01)
        print('[UART] {} {}bps 已打开'.format(COM_PORT, BAUDRATE))
    except Exception as e:
        print('[UART] 打开失败: {}'.format(e))
        uart = None
else:
    uart = None


# ============================================================
# ★ 检测目标配置 ★
#   每个颜色后面填你要的形状列表, 空列表=跳过该颜色
#   可选形状: "RECT矩形" "CIRCLE圆形" "TRIANGLE三角形"
# ============================================================
DETECT = {
    "RED":    ["CIRCLE", "TRIANGLE"],                    # 例: 只检测红色矩形
    "GREEN":  ["CIRCLE"],                  # 例: 只检测绿色圆形
    "BLUE":   ["RECT", "CIRCLE"],          # 例: 蓝色矩形+圆形
    "YELLOW": [],                          # 跳过黄色
    "PURPLE": [],                          # 跳过紫色
    "BLACK":  [],                          # 跳过黑色
}

# ============================================================
# HSV 颜色阈值
#   H: 0~180    S: 0~255    V: 0~255
#   ★ 先跑 hsv_tuner.py 获取你现场光线的准确阈值 ★
# ============================================================
COLOR_CONFIG = {
    "RED": {
        "hsv_low":  (0, 120, 80),
        "hsv_high": (10, 255, 255),
        "extra":    ((160, 120, 80), (180, 255, 255)),  # 红在HSV两端
        "draw":     (0, 0, 255),        # BGR
    },
    "GREEN": {
        "hsv_low":  (40, 80, 60),
        "hsv_high": (90, 255, 255),
        "draw":     (0, 255, 0),
    },
    "BLUE": {
        "hsv_low":  (95, 100, 60),
        "hsv_high": (130, 255, 255),
        "draw":     (255, 0, 0),
    },
    "YELLOW": {
        "hsv_low":  (20, 100, 100),
        "hsv_high": (35, 255, 255),
        "draw":     (0, 255, 255),
    },
    "PURPLE": {
        "hsv_low":  (135, 80, 60),
        "hsv_high": (160, 255, 255),
        "draw":     (255, 0, 255),
    },
    "BLACK": {
        "hsv_low":  (0, 0, 0),
        "hsv_high": (180, 255, 60),     # 只靠低V通道
        "draw":     (255, 255, 255),     # 黑色用白框标注
    },
}


# ============================================================
# 构建实际的检测列表 (根据 DETECT 过滤)
# ============================================================
def build_detect_list():
    """返回 [(颜色名, 形状, 绘图色), ...] — 仅包含 DETECT 指定的组合"""
    dl = []
    for color_name, shapes in DETECT.items():
        if not shapes:            # 空列表 → 跳过
            continue
        if color_name not in COLOR_CONFIG:
            print("[WARN] 未知颜色: {}".format(color_name))
            continue
        draw_color = COLOR_CONFIG[color_name]["draw"]
        for s in shapes:
            if s not in ("RECT", "CIRCLE", "TRIANGLE"):
                print("[WARN] 未知形状: {}".format(s))
                continue
            dl.append((color_name, s, draw_color))
    return dl


# ---- 计算 mask 的函数 (缓存上次的颜色, 避免重建) ----
def get_color_mask(hsv, color_name):
    """获取指定颜色的二值 mask (含形态学去噪)"""
    cfg = COLOR_CONFIG[color_name]
    mask = cv2.inRange(hsv, cfg["hsv_low"], cfg["hsv_high"])
    if "extra" in cfg:
        mask2 = cv2.inRange(hsv, cfg["extra"][0], cfg["extra"][1])
        mask = cv2.bitwise_or(mask, mask2)

    k = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k, iterations=2)
    return mask


# ============================================================
# 形状分类 (基于轮廓顶点数 + 圆度)
# ============================================================
def classify_shape(cnt, area):
    """返回 None / RECT / CIRCLE / TRIANGLE"""
    if area < 300:
        return None

    peri = cv2.arcLength(cnt, True)
    approx = cv2.approxPolyDP(cnt, 0.03 * peri, True)
    vertices = len(approx)

    # 圆度 = 实际面积 / 最小外接圆面积
    _, radius = cv2.minEnclosingCircle(cnt)
    if radius > 5:
        circularity = area / (np.pi * radius * radius)
    else:
        circularity = 0

    if 0.78 <= circularity <= 1.25 and vertices >= 5:
        return "CIRCLE"
    if vertices == 3:
        return "TRIANGLE"
    if 4 <= vertices <= 10:
        return "RECT"
    if 0.65 <= circularity < 0.78:
        return "TRIANGLE"
    return None


def draw_result(img, cnt, shape, color_bgr):
    """按形状画标注框/圆/三角, 返回中心坐标"""
    x, y, w, h = cv2.boundingRect(cnt)
    M = cv2.moments(cnt)
    if M["m00"] > 0:
        cx, cy = int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"])
    else:
        cx, cy = x + w // 2, y + h // 2

    if shape == "RECT":
        cv2.rectangle(img, (x, y), (x + w, y + h), color_bgr, 2)
    elif shape == "CIRCLE":
        r = max(w, h) // 2
        cv2.circle(img, (cx, cy), r, color_bgr, 2)
    elif shape == "TRIANGLE":
        cv2.drawContours(img, [cnt], -1, color_bgr, 2)
    return cx, cy


# ============================================================
# 主循环
# ============================================================
def main():
    # ---- 解析 DETECT 配置 ----
    detect_list = build_detect_list()
    if not detect_list:
        print("[ERROR] DETECT 字典里没有指定任何组合, 请修改后重试")
        print("  例: DETECT = {'RED': ['RECT'], 'BLUE': ['CIRCLE']}")
        return

    # 统计哪些颜色需要计算 mask (去重)
    active_colors = list(dict.fromkeys(c for c, _, _ in detect_list))

    # ---- 校验 ----
    print("=" * 55)
    print("  当前检测目标 (DETECT 配置):")
    for color_name, shape, _ in detect_list:
        print("    {} {}".format(color_name, shape))
    print("  活跃颜色 (会计算mask): {}".format(", ".join(active_colors)))
    print("  q=退出  s=截图  ESC=退出")
    print("  ★ 在终端窗口敲 q/s 即可 ★")
    print("=" * 55)

    # ---- 摄像头 ----
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("摄像头打不开")
        return

    win_name = "Color+Shape | {}".format(
        ", ".join("{} {}".format(c, s) for c, s, _ in detect_list[:4])
        + ("..." if len(detect_list) > 4 else ""))

    # ---- 平台按键: Windows msvcrt / Linux waitKey ----
    if sys.platform == "win32":
        import msvcrt
        def key_pressed():
            if msvcrt.kbhit():
                ch = msvcrt.getch()
                try:
                    return ch.decode("utf-8").lower()
                except UnicodeDecodeError:
                    return ch
            return None
    else:
        def key_pressed():
            return None

    # ---- 主循环 ----
    # mask 缓存: 每帧每个活跃颜色只算一次 mask, 多个形状共享
    while True:
        ok, frame = cap.read()
        if not ok:
            break

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # ---- 按需计算每个活跃颜色的 mask (去重, 缓存) ----
        mask_cache = {}
        for cn in active_colors:
            mask_cache[cn] = get_color_mask(hsv, cn)

        # ---- 对 DETECT 里的每个组合做检测 ----
        for color_name, target_shape, draw_color in detect_list:
            mask = mask_cache[color_name]

            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                           cv2.CHAIN_APPROX_SIMPLE)

            for cnt in contours:
                area = cv2.contourArea(cnt)
                shape = classify_shape(cnt, area)
                if shape != target_shape:     # ★ 只匹配指定形状
                    continue

                cx, cy = draw_result(frame, cnt, shape, draw_color)

                label = "{} {}".format(color_name, shape)
                cv2.putText(frame, label, (cx - 50, cy - 15),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                            draw_color, thickness=2)

                print("[OK] {} {}".format(color_name, shape))

        # ---- 底部状态栏 ----
        status = "q:quit  s:save  |  targets:{}  colors:{}".format(
            len(detect_list), len(active_colors))
        cv2.putText(frame, status, (10, frame.shape[0] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)

        cv2.imshow(win_name, frame)

        # ---- 按键处理 ----
        kp = key_pressed()
        if kp is not None:
            if kp == 'q':
                break
            elif kp == 's':
                cv2.imwrite("snapshot.jpg", frame)
                print("截图已保存: snapshot.jpg")
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:
            break
        elif key == ord('s'):
            cv2.imwrite("snapshot.jpg", frame)
            print("截图已保存: snapshot.jpg")

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
