import os
import cv2
import numpy as np
import onnxruntime as ort
import logging
import getcolors
 
def preprocess(image, input_width=320,input_height=320,mean=[0,0,0],std=[1,1,1]):
    """
    预处理输入图像，调整大小、归一化、转换通道顺序、添加批次维度。
    """
    # 获取原始图像尺寸
    orig_h, orig_w = image.shape[:2]
    # 计算缩放比例，保持长宽比
    scale = min(input_width / orig_w, input_height / orig_h)
    new_w = int(orig_w * scale)
    new_h = int(orig_h * scale)
    # 缩放图像
    resized_image = cv2.resize(image, (new_w, new_h))
    # 创建一个背景图像
    canvas = np.ones((input_height, input_width, 3),dtype=np.uint8)*128
    # 将缩放后的图像粘贴到背景图像中
    canvas[0:new_h, 0:new_w, :] = resized_image
    # BGR 转 RGB
    img = canvas[:, :, ::-1]
    # 转换为 float32
    img = img.astype(np.float32) / 255
    for i in range(3):
        img[:, :, i] -= mean[i]
        img[:, :, i] /= std[i]
    # HWC 转 CHW
    img = np.transpose(img, (2, 0, 1))
    # 添加批次维度
    img = np.expand_dims(img, axis=0)
    onnx_input=img.copy()
    return onnx_input, scale
 
def get_covariance_matrix(obb):
    """
    计算旋转边界框的协方差矩阵。
    :param obb: 旋转边界框 (Oriented Bounding Box)，包含中心坐标、宽、高和旋转角度
    :return: 协方差矩阵的三个元素 a, b, c
    """
    widths = obb[..., 2] / 2
    heights = obb[..., 3] / 2
    angles = obb[..., 4]
 
    cos_angle = np.cos(angles)
    sin_angle = np.sin(angles)
 
    a = (widths * cos_angle)**2 + (heights * sin_angle)**2
    b = (widths * sin_angle)**2 + (heights * cos_angle)**2
    c = widths * cos_angle * heights * sin_angle
 
    return a, b, c


def cal_rotate_iou(obb1, obb2, eps=1e-7):
    """
    计算旋转边界框之间的 ProbIoU。
    :param obb1: 第一个旋转边界框
    :param obb2: 第二个旋转边界框
    :param eps: 防止除零的极小值
    :return: 两个旋转边界框之间的 ProbIoU
    """
    # 获取当前框的中心点坐标
    x1, y1 = obb1[0], obb1[1]
    # 获取剩余框的中心点坐标
    x2, y2 = obb2[0], obb2[1]
    # 计算
    a1, b1, c1 = get_covariance_matrix(obb1)
    a2, b2, c2 = get_covariance_matrix(obb2)
 
    t1 = ((a1 + a2) * (y1 - y2)**2 + (b1 + b2) * (x1 - x2)**2) / ((a1 + a2) * (b1 + b2) - (c1 + c2)**2 + eps) * 0.25
    t2 = ((c1+ c2) * (x2 - x1) * (y1 - y2)) / ((a1 + a2) * (b1 + b2) - (c1 + c2)**2 + eps) * 0.5
    t3 = np.log(((a1 + a2) * (b1 + b2) - (c1 + c2)**2) /(4 * np.sqrt((a1 * b1 - c1**2) * (a2 * b2 - c2**2)) + eps) + eps) * 0.5
 
    bd = np.clip(t1 + t2 + t3, eps, 100.0)
    hd = np.sqrt(1.0 - np.exp(-bd) + eps)
    return 1 - hd

def calculate_obb_corners(x_center, y_center, width, height, angle):
    """
    根据旋转角度计算旋转边界框的四个角点。
    :param x_center: 边界框中心的 x 坐标
    :param y_center: 边界框中心的 y 坐标
    :param width: 边界框的宽度
    :param height: 边界框的高度
    :param angle: 旋转角度
    :return: 旋转边界框的四个角点坐标
    """
    cos_angle = np.cos(angle)  # 计算旋转角度的余弦值
    sin_angle = np.sin(angle)  # 计算旋转角度的正弦值
    dx = width / 2  # 计算宽度的一半
    dy = height / 2  # 计算高度的一半
 
    # 计算旋转边界框的四个角点坐标
    corners = [
        (int(x_center + cos_angle * dx - sin_angle * dy), int(y_center + sin_angle * dx + cos_angle * dy)),
        (int(x_center - cos_angle * dx - sin_angle * dy), int(y_center - sin_angle * dx + cos_angle * dy)),
        (int(x_center - cos_angle * dx + sin_angle * dy), int(y_center - sin_angle * dx - cos_angle * dy)),
        (int(x_center + cos_angle * dx + sin_angle * dy), int(y_center + sin_angle * dx - cos_angle * dy)),
    ]
    return corners  # 返回角点坐标
 

def postprocess(output, scale, conf_threshold=0.5, iou_threshold=0.5):
    """
    解析ONNX模型的输出，提取旋转边界框坐标、置信度和类别信息，并应用旋转NMS。
    :param output: ONNX模型的输出，包含预测的边界框信息
    :param scale: 缩放比例，用于将坐标还原到原始尺度
    :param conf_threshold: 置信度阈值，过滤低于该阈值的检测框
    :param iou_threshold: IoU 阈值，用于旋转边界框的非极大值抑制（NMS）
    :return: 符合条件的旋转边界框的检测结果
    """
    boxes, scores, classes, detections = [], [], [], []
    num_detections = output.shape[2]  # 获取检测的边界框数量
    num_classes = output.shape[1] - 5  # 计算类别数量
    output_=np.transpose(output,(0,2,1))
 
    # 逐个解析每个检测结果
    for i in range(num_detections):
        detection = output_[0, i, :]
        x_center, y_center, width, height = detection[0], detection[1], detection[2], detection[3]  # 提取边界框的中心坐标和宽高
        angle = detection[-1]  # 提取旋转角度
 
        if num_classes > 0:
            class_confidences = detection[4:4 + num_classes]  # 获取类别置信度
            if class_confidences.size == 0:
                continue
            class_id = np.argmax(class_confidences)  # 获取置信度最高的类别索引
            confidence = class_confidences[class_id]  # 获取对应的置信度
        else:
            confidence = detection[4]  # 如果没有类别信息，直接使用置信度值
            class_id = 0  # 默认类别为 0
 
        if confidence > conf_threshold:  # 过滤掉低置信度的检测结果
            x_center = (x_center) / scale  # 还原中心点 x 坐标
            y_center = (y_center) / scale  # 还原中心点 y 坐标
            width /= scale  # 还原宽度
            height /= scale  # 还原高度
 
            boxes.append([x_center, y_center, width, height, angle])  # 将边界框信息加入列表
            scores.append(confidence)  # 将置信度加入列表
            classes.append(class_id)  # 将类别加入列表
 
    if not boxes:
        return []
 
    # 转换为 NumPy 数组
    boxes = np.array(boxes)
    scores = np.array(scores)
    classes = np.array(classes)

    keep_indices=[]
    order = scores.argsort()[::-1]  # 根据置信度得分降序排序
    for i in range(len(order)):
        i_idx = order[i]
        if i_idx!=-1:
            keep_indices.append(i_idx)
        else:
            continue
        remaining_boxes = boxes[order[1:]]
        for j in range(1, len(order)):
            j_idx = order[j]
            iou_values = cal_rotate_iou(boxes[i_idx], boxes[j_idx])
            if iou_values > iou_threshold:
                order[j] = -1
 
    # 构建最终检测结果
    for idx in keep_indices:
        x_center, y_center, width, height, angle = boxes[idx]  # 获取保留的边界框信息
        confidence = scores[idx]  # 获取对应的置信度
        class_id = classes[idx]  # 获取类别
        obb_corners = calculate_obb_corners(x_center, y_center, width, height, angle)  # 计算旋转边界框的四个角点
 
        detections.append({
            "position": obb_corners,  # 旋转边界框的角点坐标
            "confidence": float(confidence),  # 置信度
            "class_id": int(class_id),  # 类别 ID
            "angle": float(angle)  # 旋转角度
        })
 
    return detections
 
def draw_result(image, detections, class_names,colors):
    """
    在图像上绘制旋转边界框检测结果并保存。
    :param image: 原始图像
    :param detections: 检测结果列表
    :param class_names: 标签名称
    :param colors: 颜色列表
    """
    for det in detections:
        corners = det['position']  # 获取旋转边界框的四个角点
        confidence = det['confidence']  # 获取置信度
        class_id = det['class_id']  # 获取类别ID
 
        # 绘制边界框的四条边
        for j in range(4):
            pt1 = corners[j]
            pt2 = corners[(j + 1) % 4]
            cv2.line(image, pt1, pt2, colors[class_id], 2)
        
        # 在边界框上方显示类别和置信度
        cv2.putText(image, str(class_id), (corners[0][0], corners[0][1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 1.0, colors[class_id], 3)
    return image

if __name__ == "__main__":
    # 设置参数
    model_path = '../../runs/obb/train/weights/best.onnx'  # 替换为你的 ONNX 模型路径
    image_path = '../test_images/test_pen.jpg'  # 替换为你要检测的图像路径
    input_width = 320
    input_height = 320
    mean=[0,0,0]
    std=[1,1,1]
    conf_threshold = 0.1
    iou_threshold = 0.6
    # 加载类别名称（根据你的数据集修改）
    class_names = ['pen']
    colors=getcolors.get_colors(len(class_names))
    # 加载 ONNX 模型
    ort_session = ort.InferenceSession(model_path)
    # 获取模型输入名称
    input_name = ort_session.get_inputs()[0].name

    # 读取图像
    image = cv2.imread(image_path)
    if image is None:
        print(f"Error: 无法读取图像 {image_path}")
    # 预处理图像
    img_input, scale = preprocess(image, input_width,input_height,mean,std)

    # 运行推理
    outputs = ort_session.run(None, {input_name: img_input})
    # 假设模型只有一个输出
    predictions = outputs[0]
    detections = postprocess(predictions, scale, conf_threshold=conf_threshold, iou_threshold=iou_threshold)  # 解析输出
    # 绘制检测结果
    result_image = draw_result(image.copy(), detections, class_names, colors)
    # 保存结果图像
    cv2.imwrite("onnx_obb_result.jpg", result_image)
    print("onnx_obb_result.jpg is saved!")