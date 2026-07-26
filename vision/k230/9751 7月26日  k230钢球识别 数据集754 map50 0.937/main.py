from libs.PipeLine import PipeLine
from libs.YOLO import YOLO11
from libs.Utils import *
from media.sensor import *
import os, sys, gc
import ulab.numpy as np
import image
import time

# ---------- 导入串口库 ----------
from machine import UART, FPIOA

# ---------- 配置参数 ----------
kmodel_path = "/sdcard/yolo11n_det_320.kmodel"
labels = {0: 'ball'}
model_input_size = [320, 320]
display = "lcd3_5"

if display == "hdmi":
    display_mode = "hdmi"
    display_size = [1920, 1080]
elif display == "lcd3_5":
    display_mode = "st7701"
    display_size = [800, 480]
elif display == "lcd2_4":
    display_mode = "st7701"
    display_size = [640, 480]

rgb888p_size = [640, 360]

# ---------- 串口初始化 ----------
UART_BAUD = 115200
fpioa = FPIOA()
fpioa.set_function(3, fpioa.UART1_TXD)
fpioa.set_function(4, fpioa.UART1_RXD)
uart = UART(UART.UART1, baudrate=UART_BAUD, bits=UART.EIGHTBITS,
            parity=UART.PARITY_NONE, stop=UART.STOPBITS_ONE)

# 初始化PipeLine
pl = PipeLine(
    rgb888p_size=rgb888p_size, display_size=display_size, display_mode=display_mode
)

if display == "lcd2_4":
    pl.create(sensor=Sensor(id=2, width=1280, height=960))  # 创建PipeLine实例，摄像头csi2, 画面4:3
else:
    pl.create(sensor=Sensor(id=2, width=1920, height=1080))  # 创建PipeLine实例,摄像头csi2

display_size = pl.get_display_size()

# ---------- 初始化YOLO11实例 ----------
confidence_threshold = 0.6  # 置信度
nms_threshold = 0.45
yolo = YOLO11(
    task_type="detect",
    mode="video",
    kmodel_path=kmodel_path,
    labels=labels,
    rgb888p_size=rgb888p_size,
    model_input_size=model_input_size,
    display_size=display_size,
    conf_thresh=confidence_threshold,
    nms_thresh=nms_threshold,
    max_boxes_num=50,
    debug_mode=0,
)
yolo.config_preprocess()

clock = time.clock()

# ---------- 画面绘制函数（显示坐标、置信度和总数） ----------
def draw_detection_info(osd_img, detections, labels):
    count = len(detections) if detections is not None else 0
    # 左上角显示总数
    osd_img.draw_string(10, 10, "Total: {}".format(count), color=(255, 255, 0), scale=2, thickness=2)

    if detections is not None and len(detections) > 0:
        for det in detections:
            try:
                bbox = det.bbox()
                conf = det.confidence()
            except AttributeError:
                bbox = det[0:4]
                conf = det[4]
            x1, y1, x2, y2 = bbox
            center_x = int((x1 + x2) / 2)
            center_y = int((y1 + y2) / 2)
            # 每个框上方显示：类别名 (坐标) 置信度
            info_str = "{} ({},{}) {:.2f}".format(labels[0], center_x, center_y, conf)
            text_x = int(x1)
            text_y = int(y1) - 15
            if text_y < 10:
                text_y = int(y2) + 15
            osd_img.draw_string(text_x, text_y, info_str, color=(0, 255, 255), scale=1.5, thickness=2)

# 串口发送函数
def send_detection_results(uart, detections):

    count = len(detections) if detections is not None else 0

    # 如果没有检测到目标，直接发送 "0\n"
    if count == 0:
        uart.write("0\n")
        return

    # 构建发送字符串：先写入总数
    send_str = str(count)

    # 遍历每个检测目标，追加 (X,Y)
    for det in detections:
        try:
            bbox = det.bbox()
        except AttributeError:
            bbox = det[0:4]
        x1, y1, x2, y2 = bbox
        center_x = int((x1 + x2) / 2)
        center_y = int((y1 + y2) / 2)

        send_str += "({},{})".format(center_x, center_y)

    # 末尾加换行符，表示一帧数据结束
    send_str += "\n"

    # 通过串口发送
    uart.write(send_str)


# ---------- 主循环 ----------
while True:
    clock.tick()

    # 逐帧推理
    img = pl.get_frame()
    res = yolo.run(img)
    yolo.draw_result(res, pl.osd_img)

    # 1. 画面叠加信息
    draw_detection_info(pl.osd_img, res, labels)

    # 2. 串口发送数据
    send_detection_results(uart, res)

    # 显示画面
    pl.show_image()
    gc.collect()

    # 打印帧率（若觉得干扰可注释掉）
    print("FPS:", clock.fps())

# 释放资源
yolo.deinit()
pl.destroy()
uart.deinit()
