#include "ti_msp_dl_config.h"
#include "Board.h"
#include "TB6612.h"
#include "OLED.h"
#include "JY60.h"
#include "GraySensor.h"
#include "tracking.h"
#include "buzzer.h"
#include "turn.h"

/* ============================================================
 * 任务选择：修改 TASK_SELECT 为 1~4 选择任务
 *   1 = A→B 直行
 *   2 = A→B→C→D→A 完整一圈
 *   3 = A→C→B→D→A 反向一圈
 *   4 = 任务3 × 4圈
 * ============================================================ */
#define TASK_SELECT  1

/* 距离参数 (cm) */
#define DIST_AB    80      /* 上直边 A-B */
#define DIST_CD    80      /* 下直边 C-D */
#define DIST_DIAG  113     /* 对角线 A-C / B-D, sqrt(80^2+80^2) */

/* 速度参数 */
#define SPEED_STRAIGHT  500
#define SPEED_ARC       350

/* 循线丢失确认计数（×10ms） */
#define LINE_LOST_COUNT 30   /* 300ms 连续失线 = 弧线终点 */

/* ============================================================
 * 全局变量
 * ============================================================ */
uint16_t Roll, Pitch, Yaw;

/* ============================================================
 * 循线弧线段
 * 沿黑线走完弧线，直到线消失（进入直行段）
 * ============================================================ */
static void follow_arc(int32_t base_speed)
{
    PID_Controller pid;
    uint8_t  lost_count = 0;
    int32_t  last_correction = 0;

    PID_Init(&pid, 1.0f, 0.02f, 0.5f, 350);

    while (1)
    {
        uint16_t pos = GraySensor_GetPosition();

        if (tracking_LineLost(pos))
        {
            lost_count++;
            if (lost_count > LINE_LOST_COUNT)
            {
                /* 线持续丢失 → 弧线终点 */
                break;
            }
            /* 短暂失线：用上一次修正值继续 */
            tracking_ApplySteering(base_speed, last_correction);
        }
        else
        {
            lost_count = 0;
            last_correction = tracking_ComputeSteering(&pid, pos);
            tracking_ApplySteering(base_speed, last_correction);
        }

        delay_ms(10);
    }

    TB6612_Motor_Stop();
    PID_Reset(&pid);
}

/* ============================================================
 * 任务 1：A → B  直行 80cm
 * ============================================================ */
static void task1_A_to_B(void)
{
    OLED_Clear();
    OLED_ShowString(1, 1, "Task1: A->B");

    advance_IMU(SPEED_STRAIGHT, DIST_AB);

    Signal_Point('B');

    OLED_ShowString(2, 1, "Done!");
}

/* ============================================================
 * 任务 2：A→B→右弧→C→D→左弧→A  完整一圈
 * ============================================================ */
static void task2_full_loop(void)
{
    OLED_Clear();
    OLED_ShowString(1, 1, "Task2: Full Loop");

    /* A 点出发 */
    Signal_Point('A');

    /* A→B 直行 */
    OLED_ShowString(2, 1, "A->B");
    advance_IMU(SPEED_STRAIGHT, DIST_AB);
    Signal_Point('B');

    /* B→C 右弧循线 */
    OLED_ShowString(2, 1, "B->C arc");
    delay_ms(100);
    follow_arc(SPEED_ARC);
    Signal_Point('C');

    /* C→D 直行 */
    OLED_ShowString(2, 1, "C->D");
    advance_IMU(SPEED_STRAIGHT, DIST_CD);
    Signal_Point('D');

    /* D→A 左弧循线 */
    OLED_ShowString(2, 1, "D->A arc");
    delay_ms(100);
    follow_arc(SPEED_ARC);
    Signal_Point('A');

    OLED_ShowString(2, 1, "Done!");
}

/* ============================================================
 * 任务 3：A→C→右弧→B→D→左弧→A  反向一圈
 * ============================================================ */
static void task3_reverse_loop(void)
{
    OLED_Clear();
    OLED_ShowString(1, 1, "Task3: Rev Loop");

    /* A 点出发 */
    Signal_Point('A');

    /* A→C 对角线直行（无黑线） */
    OLED_ShowString(2, 1, "A->C diag");
    advance_IMU(SPEED_STRAIGHT, DIST_DIAG);
    Signal_Point('C');

    /* C→B 右弧逆向循线 */
    OLED_ShowString(2, 1, "C->B arc");
    delay_ms(100);
    follow_arc(SPEED_ARC);
    Signal_Point('B');

    /* B→D 对角线直行 */
    OLED_ShowString(2, 1, "B->D diag");
    advance_IMU(SPEED_STRAIGHT, DIST_DIAG);
    Signal_Point('D');

    /* D→A 左弧循线 */
    OLED_ShowString(2, 1, "D->A arc");
    delay_ms(100);
    follow_arc(SPEED_ARC);
    Signal_Point('A');

    OLED_ShowString(2, 1, "Done!");
}

/* ============================================================
 * 任务 4：任务 3 × 4 圈
 * ============================================================ */
static void task4_four_loops(void)
{
    uint8_t lap;

    OLED_Clear();
    OLED_ShowString(1, 1, "Task4: 4 Loops");

    Signal_Point('A');

    for (lap = 0; lap < 4; lap++)
    {
        OLED_ShowString(2, 1, "Lap: ");
        OLED_ShowNum(2, 6, lap + 1, 1);

        /* A→C */
        advance_IMU(SPEED_STRAIGHT, DIST_DIAG);
        Signal_Point('C');

        /* C→B 右弧 */
        follow_arc(SPEED_ARC);
        Signal_Point('B');

        /* B→D */
        advance_IMU(SPEED_STRAIGHT, DIST_DIAG);
        Signal_Point('D');

        /* D→A 左弧 */
        follow_arc(SPEED_ARC);
        Signal_Point('A');
    }

    OLED_ShowString(2, 1, "Done!");
}

/* ============================================================
 * 主函数
 * ============================================================ */
int main(void)
{
    SYSCFG_DL_init();
    TB6612_Motor_Stop();
    Serial_Init();
    Buzzer_LED_Init();
    OLED_Init();
    GraySensor_Init();

    OLED_Clear();
    OLED_ShowString(1, 1, "Ready T:");
    OLED_ShowNum(1, 9, TASK_SELECT, 1);

    delay_ms(1000);  /* 上电等待 1 秒 */

    switch (TASK_SELECT)
    {
    case 1:
        task1_A_to_B();
        break;
    case 2:
        task2_full_loop();
        break;
    case 3:
        task3_reverse_loop();
        break;
    case 4:
        task4_four_loops();
        break;
    default:
        OLED_ShowString(2, 1, "Invalid Task");
        break;
    }

    /* 任务完成后停车，闪烁 LED */
    while (1)
    {
        LED_On();
        delay_ms(500);
        LED_Off();
        delay_ms(500);
    }
}
