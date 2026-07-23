#ifndef _BSP_TRACKING_H
#define _BSP_TRACKING_H

#include <stdint.h>

/* 目标位置：线在传感器正中间 (3.5 * 1000 = 3500) */
#define LINE_TARGET_POSITION    3500

/* PID 控制器参数结构体 */
typedef struct {
    float    Kp;
    float    Ki;
    float    Kd;
    int32_t  integral;
    int32_t  last_error;
    int32_t  max_integral;
    int32_t  max_output;       /* 修正量上限 */
} PID_Controller;

void    PID_Init(PID_Controller *pid, float Kp, float Ki, float Kd, int32_t max_output);
int32_t PID_Compute(PID_Controller *pid, int32_t setpoint, int32_t measurement);
void    PID_Reset(PID_Controller *pid);

/* 循线控制：根据线位置计算转向修正，并施加到左右电机 */
int32_t tracking_ComputeSteering(PID_Controller *pid, uint16_t line_position);
void    tracking_ApplySteering(int32_t base_speed, int32_t correction);

/* 判断是否失去黑线（弧线终点检测） */
uint8_t tracking_LineLost(uint16_t line_position);

#endif /* _BSP_TRACKING_H */
