"""
OpenCV 颜色+形状联合识别 (PC端模拟 K230)
==========================================
6颜色(红/绿/蓝/黄/紫/黑) × 3形状(矩形/圆形/三角形)
共计18种组合, 实时视频流检测

用法:
  pip install opencv-python numpy
  python cv_color_shape.py

按键:
  q - 退出
  s - 截图保存为 snapshot.jpg
"""

import cv2
import numpy as np

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
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("摄像头打不开")
        return

    print("=" * 55)
    print("  颜色+形状识别 | 6颜色 x 3形状 = 18种组合")
    print("  RED/GREEN/BLUE/YELLOW/PURPLE/BLACK")
    print("  RECT / CIRCLE / TRIANGLE")
    print("  q=退出  s=截图")
    print("=" * 55)

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        for color_name, cfg in COLOR_CONFIG.items():
            # 构建该颜色的 mask
            mask = cv2.inRange(hsv, cfg["hsv_low"], cfg["hsv_high"])
            if "extra" in cfg:
                mask2 = cv2.inRange(hsv, cfg["extra"][0], cfg["extra"][1])
                mask = cv2.bitwise_or(mask, mask2)

            # 形态学去噪
            k = np.ones((5, 5), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k, iterations=1)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k, iterations=2)

            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                           cv2.CHAIN_APPROX_SIMPLE)

            for cnt in contours:
                area = cv2.contourArea(cnt)
                shape = classify_shape(cnt, area)
                if shape is None:
                    continue

                cx, cy = draw_result(frame, cnt, shape, cfg["draw"])

                label = "{} {}".format(color_name, shape)
                cv2.putText(frame, label, (cx - 50, cy - 15),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                            cfg["draw"], thickness=2)

                print("[OK] {} {}".format(color_name, shape))

        # 底部提示
        cv2.putText(frame, "q:quit  s:save",
                    (10, frame.shape[0] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        cv2.imshow("Color+Shape (6x3=18 combos)", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            cv2.imwrite("snapshot.jpg", frame)
            print("截图已保存: snapshot.jpg")

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
