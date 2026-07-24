"""
EasyOCR 汉字自动标注采集脚本
=============================
用 EasyOCR 识别 USB 摄像头中的手写汉字, 按 s 保存为 YOLO 训练格式

输出:
  dataset_cn/images/  - 训练图片
  dataset_cn/labels/  - YOLO 标注 (class_id cx cy w h)
  dataset_cn/classes.txt - 汉字→ID映射表

用法:
  1. pip install easyocr opencv-python==4.10.0.84 numpy
  2. 修改下面的 TARGET_CHARS, 填上你要识别的汉字
  3. python easyocr_collect_cn.py
  4. 每个字写下来放摄像头前 → 识别对了按 s 保存
  5. 每个字收集 50~100 张, 按 q 退出

按键:
  s - 保存    q - 退出    c - 显示/隐藏置信度    1~9 - 切换当前采集字
  u - 撤销刚保存的    p - 暂停/继续自动保存
"""

import cv2
import numpy as np
import os
import sys
import time
import easyocr
import json

# ---- GUI 检测 ----
try:
    cv2.imshow("_test", np.zeros((1, 1, 3), dtype=np.uint8))
    cv2.destroyWindow("_test")
    HAS_GUI = True
except:
    HAS_GUI = False
    print("OpenCV 无 GUI → 终端模式 (功能正常)")

# ============================================================
# ★ 配置: 要识别的汉字列表 ★
#   改这里就行, 顺序固定后训练时就按这个顺序
#   例: 电赛识别 "左""右""停""行""上""下""前""后"
# ============================================================
TARGET_CHARS = ["左", "右", "停", "行", "上", "下", "前", "后",
                "开", "关", "进", "出"]

# ============================================================
# 自动保存配置
# ============================================================
AUTO_SAVE = True           # True=自动保存(置信度高时自动存)  False=手动按s
AUTO_CONF = 0.75           # 自动保存的置信度门槛
AUTO_INTERVAL = 0.5        # 自动保存最小间隔(秒), 避免同一帧重复保存

# ============================================================
# 初始化
# ============================================================
SAVE_DIR = "dataset_cn"
os.makedirs(f"{SAVE_DIR}/images", exist_ok=True)
os.makedirs(f"{SAVE_DIR}/labels", exist_ok=True)

# 汉字→ID 映射
char_to_id = {ch: i for i, ch in enumerate(TARGET_CHARS)}
id_to_char = {i: ch for ch, i in char_to_id.items()}

# 保存映射表
with open(f"{SAVE_DIR}/classes.txt", 'w', encoding='utf-8') as f:
    for ch, i in char_to_id.items():
        f.write(f"{i}: {ch}\n")
with open(f"{SAVE_DIR}/char_map.json", 'w', encoding='utf-8') as f:
    json.dump({"char_to_id": char_to_id, "id_to_char": id_to_char},
              f, ensure_ascii=False, indent=2)

print(f"目标汉字: {TARGET_CHARS}")
print(f"  ID映射: {char_to_id}")
print(f"  已保存到 {SAVE_DIR}/classes.txt")

# EasyOCR
print("加载 EasyOCR 中文模型 (首次 ~200MB, 请稍候)...")
reader = easyocr.Reader(
    ['ch_sim'],
    gpu=True,
    model_storage_directory="./models"
)
print("EasyOCR 就绪!")

# 摄像头
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("摄像头打不开"); exit(1)

# 状态变量
saved_count = 0
show_conf = True
frame_skip = 0
last_results = []
last_save_time = 0  # 自动保存计时
current_char_hint = TARGET_CHARS[0]  # 当前正在采集的字(提示用)
per_char_count = {ch: 0 for ch in TARGET_CHARS}
auto_paused = False  # 自动保存暂停标志

# 按键
def key_pressed():
    if sys.platform == "win32":
        import msvcrt
        if msvcrt.kbhit():
            ch = msvcrt.getch()
            try: return ch.decode("utf-8").lower()
            except: return ch
    return None


print("=" * 60)
print("  汉字自动标注采集")
print(f"  目标: {TARGET_CHARS}")
print(f"  模式: {'自动保存(置信度>{})'.format(AUTO_CONF) if AUTO_SAVE else '手动保存'}")
print("  s=保存  q=退出  c=置信度  1~9=切换采集字  u=撤销  p=暂停")
print("=" * 60)


# ============================================================
# 主循环
# ============================================================
while True:
    ok, frame = cap.read()
    if not ok: break

    display = frame.copy()
    h, w = display.shape[:2]

    # 每3帧跑一次 OCR
    frame_skip += 1
    if frame_skip >= 3:
        frame_skip = 0
        last_results = reader.readtext(frame, detail=1, paragraph=False)
    results = last_results

    # ---- 过滤: 只保留目标汉字 ----
    filtered = []
    for bbox, text, conf in results:
        if not text or conf < 0.3:
            continue
        # 只取文本里属于 TARGET_CHARS 的字
        chars_found = [ch for ch in text if ch in char_to_id]
        if not chars_found:
            continue
        filtered.append((bbox, chars_found, conf))

    # ---- 自动保存 ----
    if AUTO_SAVE and not auto_paused:
        now = time.time()
        if now - last_save_time >= AUTO_INTERVAL:
            for bbox, chars_found, conf in filtered:
                if conf >= AUTO_CONF:
                    # 只保存置信度高的
                    pts = np.array(bbox, dtype=np.int32)
                    x_min = float(pts[:, 0].min())
                    y_min = float(pts[:, 1].min())
                    x_max = float(pts[:, 0].max())
                    y_max = float(pts[:, 1].max())

                    fname = f"cn_{saved_count:04d}"
                    cv2.imwrite(f"{SAVE_DIR}/images/{fname}.jpg", frame)

                    with open(f"{SAVE_DIR}/labels/{fname}.txt", 'w') as f:
                        for ch in chars_found:
                            class_id = char_to_id[ch]
                            cx = ((x_min + x_max) / 2) / w
                            cy = ((y_min + y_max) / 2) / h
                            bw = (x_max - x_min) / w
                            bh = (y_max - y_min) / h
                            f.write(f"{class_id} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}\n")

                    saved_count += 1
                    last_save_time = now
                    for ch in chars_found:
                        per_char_count[ch] = per_char_count.get(ch, 0) + 1

                    ch_str = "".join(chars_found)
                    print(f"[AUTO #{saved_count}] {ch_str}  {conf:.2f}")
                    break  # 一帧只存一次

    # ---- 画框 ----
    for bbox, chars_found, conf in filtered:
        pts = np.array(bbox, dtype=np.int32)
        x_min = int(pts[:, 0].min())
        y_min = int(pts[:, 1].min())
        x_max = int(pts[:, 0].max())
        y_max = int(pts[:, 1].max())

        ch_str = "".join(chars_found)
        label = ch_str if not show_conf else f"{ch_str} {conf:.2f}"

        # 绿框 + 标签
        cv2.rectangle(display, (x_min, y_min), (x_max, y_max),
                      (0, 255, 0), 2)
        cv2.putText(display, label, (x_min, y_min - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)

    # ---- 右上角: 每类统计 ----
    y_offset = 40
    cv2.putText(display, "PER CLASS:", (w - 220, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
    for ch, cnt in sorted(per_char_count.items(), key=lambda x: -x[1]):
        y_offset += 22
        cv2.putText(display, f"  {ch}: {cnt}", (w - 220, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 0), 1)

    # ---- 左上: 当前采集字提示 ----
    cv2.putText(display, f"CURRENT: {current_char_hint}",
                (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

    # ---- 底部: 状态 + 进度条 ----
    total_target = len(TARGET_CHARS) * 50  # 每类目标50张
    pct = min(saved_count / max(total_target, 1), 1.0)
    bar_w = int(w * 0.6)
    bar_x = (w - bar_w) // 2
    bar_y = h - 30
    cv2.rectangle(display, (bar_x, bar_y), (bar_x + bar_w, bar_y + 12),
                  (100, 100, 100), -1)
    cv2.rectangle(display, (bar_x, bar_y),
                  (bar_x + int(bar_w * pct), bar_y + 12),
                  (0, 255, 0), -1)
    cv2.putText(display, f"{saved_count}/{total_target}",
                (bar_x + 5, bar_y + 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)

    auto_status = "PAUSED" if auto_paused else "AUTO"
    status = f"{auto_status} | s=save q=quit c=conf p=pause u=undo | {saved_count} saved"
    cv2.putText(display, status, (10, h - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 200, 200), 1)

    if HAS_GUI:
        cv2.imshow("EasyOCR 汉字采集", display)

    # ---- 按键 ----
    kp = key_pressed()
    if kp == 'q':
        break
    elif kp == 's':
        # 手动保存
        if not filtered:
            print("当前帧没有识别到目标汉字")
            continue
        bbox, chars_found, conf = filtered[0]
        pts = np.array(bbox, dtype=np.int32)
        x_min = float(pts[:, 0].min())
        y_min = float(pts[:, 1].min())
        x_max = float(pts[:, 0].max())
        y_max = float(pts[:, 1].max())

        fname = f"cn_{saved_count:04d}"
        cv2.imwrite(f"{SAVE_DIR}/images/{fname}.jpg", frame)

        with open(f"{SAVE_DIR}/labels/{fname}.txt", 'w') as f:
            for ch in chars_found:
                class_id = char_to_id[ch]
                cx = ((x_min + x_max) / 2) / w
                cy = ((y_min + y_max) / 2) / h
                bw = (x_max - x_min) / w
                bh = (y_max - y_min) / h
                f.write(f"{class_id} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}\n")

        saved_count += 1
        for ch in chars_found:
            per_char_count[ch] = per_char_count.get(ch, 0) + 1
        ch_str = "".join(chars_found)
        print(f"[SAVED #{saved_count}] {ch_str}  {conf:.2f}")

    elif kp == 'c':
        show_conf = not show_conf
        print(f"置信度: {'ON' if show_conf else 'OFF'}")

    elif kp == 'p':
        auto_paused = not auto_paused
        print(f"自动保存: {'暂停' if auto_paused else '运行'}")

    elif kp == 'u':
        # 撤销最后一次保存
        if saved_count > 0:
            saved_count -= 1
            fname_old = f"cn_{saved_count:04d}"
            img_file = f"{SAVE_DIR}/images/{fname_old}.jpg"
            lbl_file = f"{SAVE_DIR}/labels/{fname_old}.txt"
            if os.path.exists(img_file):
                os.remove(img_file)
                os.remove(lbl_file)
                print(f"[UNDO] 已删除 #{saved_count}")

    elif kp in ['1', '2', '3', '4', '5', '6', '7', '8', '9']:
        idx = int(kp) - 1
        if idx < len(TARGET_CHARS):
            current_char_hint = TARGET_CHARS[idx]
            print(f"切换到: {current_char_hint}")

    key2 = cv2.waitKey(1) if HAS_GUI else 0xFF
    if key2 == ord('q') or key2 == 27: break

cap.release()
if HAS_GUI: cv2.destroyAllWindows()

print(f"\n采集完成! 共 {saved_count} 张")
for ch, cnt in sorted(per_char_count.items(), key=lambda x: -x[1]):
    print(f"  {ch}: {cnt} 张")
print(f"数据: {SAVE_DIR}/")
print(f"映射: {SAVE_DIR}/classes.txt")
