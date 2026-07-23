#ifndef _BSP_TURN_H
#define _BSP_TURN_H

#include <stdint.h>

/* ---- 基础运动 ---- */
void advance(void);
void turnleft(void);
void turnright(void);

/* ---- 双电机独立控制 ----
 * speed 正值=前进，负值=后退，范围 -999 ~ 999
 * Motor_Left  使用 BO1 (左电机)
 * Motor_Right 使用 AO1 (右电机)
 */
void Motor_Left(int32_t speed);
void Motor_Right(int32_t speed);
void Motor_Both(int32_t left_speed, int32_t right_speed);

/* ---- IMU 辅助直行 ----
 * 锁定初始 yaw 角，直行中 IMU 纠偏
 * speed:          基础速度 (0~999)
 * target_distance: 目标距离 (cm)
 * 通过时间估算距离（无编码器）
 * 速度-距离校准系数可在 turn.c 中调整
 */
void advance_IMU(int32_t speed, int32_t target_distance_cm);

/* ---- 停车 ---- */
void Motor_Stop(void);

#endif
