#include "tracking.h"
#include "turn.h"

/******************************************************************
 * 函 数 名 称：PID_Init
 * 函 数 说 明：初始化 PID 控制器参数
******************************************************************/
void PID_Init(PID_Controller *pid, float Kp, float Ki, float Kd, int32_t max_output)
{
    pid->Kp           = Kp;
    pid->Ki           = Ki;
    pid->Kd           = Kd;
    pid->integral     = 0;
    pid->last_error   = 0;
    pid->max_integral = max_output * 2;
    pid->max_output   = max_output;
}

/******************************************************************
 * 函 数 名 称：PID_Compute
 * 函 数 说 明：PID 计算一次迭代
 * 函 数 形 参：setpoint 目标值, measurement 当前测量值
 * 函 数 返 回：PID 输出修正值
******************************************************************/
int32_t PID_Compute(PID_Controller *pid, int32_t setpoint, int32_t measurement)
{
    int32_t error = setpoint - measurement;
    int32_t derivative;
    int32_t output;

    /* 积分项 */
    pid->integral += error;
    if (pid->integral > pid->max_integral)
    {
        pid->integral = pid->max_integral;
    }
    else if (pid->integral < -pid->max_integral)
    {
        pid->integral = -pid->max_integral;
    }

    /* 微分项 */
    derivative = error - pid->last_error;
    pid->last_error = error;

    /* PID 输出 */
    output = (int32_t)(pid->Kp * error
                     + pid->Ki * pid->integral
                     + pid->Kd * derivative);

    /* 输出限幅 */
    if (output > pid->max_output)
    {
        output = pid->max_output;
    }
    else if (output < -pid->max_output)
    {
        output = -pid->max_output;
    }

    return output;
}

/******************************************************************
 * 函 数 名 称：PID_Reset
 * 函 数 说 明：重置 PID 积分和上一次误差
******************************************************************/
void PID_Reset(PID_Controller *pid)
{
    pid->integral   = 0;
    pid->last_error = 0;
}

/******************************************************************
 * 函 数 名 称：tracking_ComputeSteering
 * 函 数 说 明：根据灰度传感器读取的位置计算转向修正值
 * 函 数 返 回：转向修正值（正值=右转，负值=左转）
******************************************************************/
int32_t tracking_ComputeSteering(PID_Controller *pid, uint16_t line_position)
{
    if (line_position == 0xFFFF)
    {
        /* 未检测到线，保持上一次修正值 */
        return pid->last_error > 0 ? pid->max_output / 4 : -pid->max_output / 4;
    }

    return PID_Compute(pid, LINE_TARGET_POSITION, (int32_t)line_position);
}

/******************************************************************
 * 函 数 名 称：tracking_ApplySteering
 * 函 数 说 明：将转向修正值施加到左右电机
 *              correction > 0 → 右转（左轮加速/右轮减速）
 *              correction < 0 → 左转（右轮加速/左轮减速）
******************************************************************/
void tracking_ApplySteering(int32_t base_speed, int32_t correction)
{
    int32_t left_speed  = base_speed;
    int32_t right_speed = base_speed;

    /*
     * correction > 0 → 线在左侧(OUT1~OUT4) → 左电机加速（越靠近OUT1加速越大）
     * correction < 0 → 线在右侧(OUT5~OUT8) → 右电机加速（越靠近OUT8加速越大）
     */
    if (correction > 0)
    {
        left_speed  = base_speed + correction;
    }
    else
    {
        right_speed = base_speed - correction;  /* correction 为负，实际是加 */
    }

    /* 限幅 */
    if (left_speed > 999)  left_speed  = 999;
    if (left_speed < 0)    left_speed  = 0;
    if (right_speed > 999) right_speed = 999;
    if (right_speed < 0)   right_speed = 0;

    Motor_Both(left_speed, right_speed);
}

/******************************************************************
 * 函 数 名 称：tracking_LineLost
 * 函 数 说 明：判断是否失去黑线（全 0）
 * 函 数 返 回：1 = 失线, 0 = 有黑线
******************************************************************/
uint8_t tracking_LineLost(uint16_t line_position)
{
    return (line_position == 0xFFFF) ? 1 : 0;
}
