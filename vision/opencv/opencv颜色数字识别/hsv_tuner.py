"""
OpenCV HSL 阈值调参工具
========================
6个滑条实时调节 H/S/V 上下限, mask窗口实时预览
目标变白、背景变黑 → 按 s 保存阈值到文件

用法:
  python hsv_tuner.py
  q=退出  s=保存阈值
"""
import cv2
import numpy as np

# ---- 默认值 (可以从这里开始拖) ----
H_LOW, H_HIGH = 0, 180
S_LOW, S_HIGH = 0, 255
V_LOW, V_HIGH = 0, 255

WINDOW = "HSV Tuner | q=quit s=save"


def nothing(x):
    pass


def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("摄像头打不开"); return

    cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW, 640, 480)
    cv2.namedWindow("Mask", cv2.WINDOW_NORMAL)

    cv2.createTrackbar("H_low",  WINDOW, 0,   180, nothing)
    cv2.createTrackbar("H_high", WINDOW, 180, 180, nothing)
    cv2.createTrackbar("S_low",  WINDOW, 0,   255, nothing)
    cv2.createTrackbar("S_high", WINDOW, 255, 255, nothing)
    cv2.createTrackbar("V_low",  WINDOW, 0,   255, nothing)
    cv2.createTrackbar("V_high", WINDOW, 255, 255, nothing)

    print("拖动滑条 → 目标变白背景变黑 → 按s保存 按q退出")

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        h_low  = cv2.getTrackbarPos("H_low",  WINDOW)
        h_high = cv2.getTrackbarPos("H_high", WINDOW)
        s_low  = cv2.getTrackbarPos("S_low",  WINDOW)
        s_high = cv2.getTrackbarPos("S_high", WINDOW)
        v_low  = cv2.getTrackbarPos("V_low",  WINDOW)
        v_high = cv2.getTrackbarPos("V_high", WINDOW)

        lower = np.array([h_low, s_low, v_low])
        upper = np.array([h_high, s_high, v_high])
        mask = cv2.inRange(hsv, lower, upper)

        # 形态学去噪
        kernel = np.ones((3, 3), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        # 找轮廓画在原图上
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > 200:
                x, y, w, h = cv2.boundingRect(cnt)
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 255), 2)
                cv2.putText(frame, "area={:.0f}".format(area),
                            (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX,
                            0.5, (0, 255, 255), 1)

        # 状态提示
        info = "HSL [{}:{}  {}:{}  {}:{}]".format(
            h_low, h_high, s_low, s_high, v_low, v_high)
        cv2.putText(frame, info, (10, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(frame, "s:save  q:quit", (10, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        cv2.imshow(WINDOW, frame)
        cv2.imshow("Mask", mask)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            vals = (h_low, h_high, s_low, s_high, v_low, v_high)
            with open("thresholds.txt", "a") as f:
                f.write("({}, {}, {}, {}, {}, {})\n".format(*vals))
            print("SAVED: ({}, {}, {}, {}, {}, {})".format(*vals))

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
