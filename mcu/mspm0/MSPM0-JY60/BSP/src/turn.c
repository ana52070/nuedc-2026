#include "turn.h"
#include "TB6612.h"
#include "ti_msp_dl_config.h"
#include "JY60.h"
#include "Board.h"

/* ============================================================
 * 速度-距离校准参数（需实测调整）
 * SPEED_TO_CM_S: 速度 1 单位对应每秒多少 cm
 * 参考值：speed=500 时约 30cm/s → 30/500 = 0.06 cm/s per unit
 * ============================================================ */
#define SPEED_TO_CM_S       0.06f

/* IMU 纠偏参数 - 比例控制 */
#define IMU_YAW_THRESHOLD   2.0f    /* yaw 偏差阈值 (°)，小于此值不纠偏 */
#define IMU_CORRECTION_GAIN 12      /* 每度偏差的速度修正量 */
#define IMU_MAX_CORRECTION  150     /* 最大修正量上限，防止过猛 */

/* ---- 已有函数（保持兼容）---- */

void advance(void)
{
    AO1_Control(1, 300);
    BO1_Control(1, 300);
}

void turnleft(void)
{
    AO1_Control(1, 500);
    BO1_Control(1, 300);
}

void turnright(void)
{
    AO1_Control(1, 300);
    BO1_Control(1, 500);
}

/* ---- 双电机独立控制 ---- */

/******************************************************************
 * 函 数 名 称：Motor_Left
 * 函 数 说 明：左电机控制 (BO1)
 * 函 数 形 参：speed 正值=前进, 负值=后退, 范围 -999~999
******************************************************************/
void Motor_Left(int32_t speed)
{
    uint8_t  dir;
    uint32_t abs_speed;

    if (speed >= 0)
    {
        dir = 1;
        abs_speed = (uint32_t)speed;
    }
    else
    {
        dir = 0;
        abs_speed = (uint32_t)(-speed);
    }

    if (abs_speed > 999) abs_speed = 999;
    BO1_Control(dir, abs_speed);
}

/******************************************************************
 * 函 数 名 称：Motor_Right
 * 函 数 说 明：右电机控制 (AO1)
 * 函 数 形 参：speed 正值=前进, 负值=后退, 范围 -999~999
******************************************************************/
void Motor_Right(int32_t speed)
{
    uint8_t  dir;
    uint32_t abs_speed;

    if (speed >= 0)
    {
        dir = 1;
        abs_speed = (uint32_t)speed;
    }
    else
    {
        dir = 0;
        abs_speed = (uint32_t)(-speed);
    }

    if (abs_speed > 999) abs_speed = 999;
    AO1_Control(dir, abs_speed);
}

/******************************************************************
 * 函 数 名 称：Motor_Both
 * 函 数 说 明：同时控制左右电机
******************************************************************/
void Motor_Both(int32_t left_speed, int32_t right_speed)
{
    Motor_Left(left_speed);
    Motor_Right(right_speed);
}

/******************************************************************
 * 函 数 名 称：Motor_Stop
 * 函 数 说 明：停止所有电机
******************************************************************/
void Motor_Stop(void)
{
    TB6612_Motor_Stop();
}

/* ---- Yaw 角度差计算（处理 0° ↔ 360° 环绕）---- */
static float yaw_diff(float current, float target)
{
    float diff = current - target;
    if (diff > 180.0f)  diff -= 360.0f;
    if (diff < -180.0f) diff += 360.0f;
    return diff;
}

/* ---- IMU 读取当前 Yaw ----
   等待 JY60 发来新一帧数据再读取，避免读到旧数据或半帧数据
   JY60 以 ~100Hz 发送，每 10ms 一帧，advance_IMU 循环也是 10ms，
   正常情况下不会超时                                           ---- */
static float get_yaw_deg(void)
{
    volatile uint32_t timeout = 10000;   /* 10ms 超时 */
    while (!Serial_GetRxFlag() && --timeout > 0)
    {
        delay_us(1);
    }

    int16_t yaw_raw = (int16_t)((Serial_RxPacket[7] << 8) | Serial_RxPacket[6]);
    return (float)yaw_raw / 100.0f;
}

/******************************************************************
 * 函 数 名 称：advance_IMU
 * 函 数 说 明：IMU 辅助直行
 *              锁定初始 yaw，行进中检测 yaw 漂移并纠偏
 *              通过时间估算距离（无编码器）
 * 函 数 形 参：speed 基础速度 (0~999)
 *              target_distance_cm 目标距离 (cm)
 * 备       注：阻塞式，函数返回时已走完目标距离
******************************************************************/
void advance_IMU(int32_t speed, int32_t target_distance_cm)
{
    float target_yaw;
    float estimated_cm_per_ms;   /* 每毫秒行进距离 (cm/ms) */
    uint32_t required_ms;
    uint32_t elapsed_ms = 0;
    uint32_t loop_delay_ms = 10; /* 每 10ms 调整一次 */

    if (speed <= 0) return;
    if (target_distance_cm <= 0) return;

    /* 读取初始 yaw 角作为目标方向 */
    target_yaw = get_yaw_deg();

    /* 距离 → 时间估算 */
    estimated_cm_per_ms = (float)speed * SPEED_TO_CM_S / 1000.0f;
    if (estimated_cm_per_ms <= 0.0f) estimated_cm_per_ms = 0.001f;
    required_ms = (uint32_t)((float)target_distance_cm / estimated_cm_per_ms);

    /* 直行循环 */
    while (elapsed_ms < required_ms)
    {
        float current_yaw;
        float diff;
        int32_t left_speed, right_speed;

        /* 读取当前 yaw */
        current_yaw = get_yaw_deg();
        diff = yaw_diff(current_yaw, target_yaw);

        /* 比例纠偏：偏差越大修正越多 */
        if (diff > IMU_YAW_THRESHOLD)
        {
            int32_t corr = (int32_t)(diff * IMU_CORRECTION_GAIN);
            if (corr > IMU_MAX_CORRECTION) corr = IMU_MAX_CORRECTION;
            left_speed  = speed + corr;
            right_speed = speed;
        }
        else if (diff < -IMU_YAW_THRESHOLD)
        {
            int32_t corr = (int32_t)(-diff * IMU_CORRECTION_GAIN);
            if (corr > IMU_MAX_CORRECTION) corr = IMU_MAX_CORRECTION;
            left_speed  = speed;
            right_speed = speed + corr;
        }
        else
        {
            left_speed  = speed;
            right_speed = speed;
        }

        /* 限幅 */
        if (left_speed  > 999) left_speed  = 999;
        if (right_speed > 999) right_speed = 999;

        Motor_Both(left_speed, right_speed);

        delay_ms(loop_delay_ms);
        elapsed_ms += loop_delay_ms;
    }

    /* 到达目标距离，停车 */
    TB6612_Motor_Stop();
}
