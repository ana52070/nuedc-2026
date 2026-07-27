# --- 导入必要的库 ---
import nncase_runtime as nn
import ulab.numpy as np
import image
import time
from machine import UART, FPIOA
from media.sensor import *
from media.display import *
from media.media import *

# ==================== 1. 配置参数 ====================
KMODEL_PATH = "/sdcard/best.kmodel"      # 修改为你的 kmodel 路径
INPUT_WIDTH = 320
INPUT_HEIGHT = 320
CONF_THRESHOLD = 0.5                     # 置信度阈值
IOU_THRESHOLD = 0.45                     # NMS 阈值
CLASS_NAME = 'ball'                      # 类别名称（仅用于显示）
BOX_COLOR = (0, 255, 0)                  # 框的颜色 (绿色)

# ==================== 2. 初始化串口 ====================
# 根据你的开发板实际引脚配置修改
fpioa = FPIOA()
fpioa.set_function(3, FPIOA.UART1_TXD)  # TX 引脚
fpioa.set_function(4, FPIOA.UART1_RXD)  # RX 引脚
uart = UART(UART.UART1, baudrate=115200)
print("串口 UART1 初始化完成！")

# ==================== 3. 加载 kmodel ====================
kpu = nn.kpu()
try:
    kpu.load_kmodel(KMODEL_PATH)
    print("kmodel 加载成功！")
except Exception as e:
    print("kmodel 加载失败:", e)
    raise e

# ==================== 4. 初始化摄像头 ====================
print("正在初始化摄像头...")
sensor = Sensor()
sensor.reset()
sensor.set_pixformat(Sensor.RGB888)
sensor.set_framesize(width=INPUT_WIDTH, height=INPUT_HEIGHT)


Display.init(Display.VIRT, width=INPUT_WIDTH, height=INPUT_HEIGHT)
MediaManager.init()
print("摄像头初始化完成！")

# ==================== 5. 后处理函数 ====================
def postprocess(output_data, conf_threshold=0.5, iou_threshold=0.45):
    predictions = output_data[0].transpose()  # shape: [2100, 5]
    
    # 提取边界框和置信度
    boxes = predictions[:, :4]   # [cx, cy, w, h] 归一化坐标
    scores = predictions[:, 4]   # 置信度

    # 过滤低分框
    mask = scores > conf_threshold
    boxes = boxes[mask]
    scores = scores[mask]

    if len(boxes) == 0:
        return []

    # 将归一化坐标映射到图像尺寸 (320x320)
    cx = boxes[:, 0] * INPUT_WIDTH
    cy = boxes[:, 1] * INPUT_HEIGHT
    w = boxes[:, 2] * INPUT_WIDTH
    h = boxes[:, 3] * INPUT_HEIGHT

    # 转换为 xyxy 格式用于 NMS
    x1 = cx - w/2
    y1 = cy - h/2
    x2 = cx + w/2
    y2 = cy + h/2
    bboxes = np.stack([x1, y1, x2, y2], axis=1)

    # 调用 image.nms 进行非极大抑制
    bbox_list = [(int(bboxes[i,0]), int(bboxes[i,1]), int(bboxes[i,2]), int(bboxes[i,3]), float(scores[i])) for i in range(len(scores))]
    keep = image.nms(bbox_list, iou_threshold, 0)

    # 构建检测结果列表
    detections = []
    for idx in keep:
        det = bbox_list[idx]
        cx = (det[0] + det[2]) // 2
        cy = (det[1] + det[3]) // 2
        w = det[2] - det[0]
        h = det[3] - det[1]
        score = det[4]
        detections.append({
            'cx': cx, 'cy': cy,
            'w': w, 'h': h,
            'score': score
        })
    return detections

# ==================== 6. 主循环 ====================
print("开始实时推理...")
while True:
    try:
        # 6.1 获取一帧图像
        img = sensor.snapshot()

        # 6.2 预处理：转换为模型输入张量
        img_data = img.to_bytes()
        input_tensor = nn.from_numpy(np.frombuffer(img_data, dtype=np.uint8).reshape((1, 3, INPUT_HEIGHT, INPUT_WIDTH)))

        # 6.3 推理
        kpu.set_input_tensor(0, input_tensor)
        kpu.run()

        # 6.4 获取输出
        output_tensor = kpu.get_output_tensor(0)
        output_data = output_tensor.to_numpy()

        # 6.5 后处理
        detections = postprocess(output_data, CONF_THRESHOLD, IOU_THRESHOLD)

        # ========== 6.6 绘制检测结果并发送坐标 ==========
        for det in detections:
            cx, cy, w, h = det['cx'], det['cy'], det['w'], det['h']
            score = det['score']

            # 计算矩形框坐标
            x1 = int(cx - w/2)
            y1 = int(cy - h/2)
            x2 = int(cx + w/2)
            y2 = int(cy + h/2)

            # ---- 绘制绿色矩形框 ----
            img.draw_rectangle(x1, y1, x2 - x1, y2 - y1, color=BOX_COLOR, thickness=2)

            # ---- 显示置信度（在框上方） ----
            label = f"{CLASS_NAME} {score:.2f}"
            img.draw_string(x1, y1 - 15, label, color=BOX_COLOR, scale=1.5, mono_space=False)

            # ---- 显示坐标（在框下方） ----
            coord_text = f"X:{cx} Y:{cy}"
            img.draw_string(x1, y2 + 5, coord_text, color=BOX_COLOR, scale=1.2, mono_space=False)

            # ---- 通过串口发送数据 ----
            send_data = f"X:{cx},Y:{cy},W:{w},H:{h},S:{score:.2f}\n"
            uart.write(send_data)
            print("串口已发送:", send_data.strip())

        # 6.7 显示绘制后的图像
        Display.show_image(img)

    except KeyboardInterrupt:
        print("用户中断，程序退出。")
        break
    except Exception as e:
        print("运行出错:", e)
        continue

# ==================== 7. 释放资源 ====================
# 程序通常不会执行到这里
print("程序结束。")