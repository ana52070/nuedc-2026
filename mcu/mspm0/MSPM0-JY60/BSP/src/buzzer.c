#include "buzzer.h"
#include "ti_msp_dl_config.h"
#include "Board.h"

/******************************************************************
 * 函 数 名 称：Buzzer_LED_Init
 * 函 数 说 明：蜂鸣器 + LED GPIO 初始化
 *              PB0 (LED) → IOMUX_PINCM12 (GPIOB_DIO00), 输出
 *              PB1 (蜂鸣器) → IOMUX_PINCM13 (GPIOB_DIO01), 输出
******************************************************************/
void Buzzer_LED_Init(void)
{
    /* 先配置引脚为输出模式，再使能输出，最后拉低
     * 顺序不能反——配置输出之前 clearPins 无效 */

    /* PB0 = LED 输出 */
    DL_GPIO_initDigitalOutput(IOMUX_PINCM12);
    DL_GPIO_enableOutput(GPIOB, DL_GPIO_PIN_0);

    /* PB1 = 蜂鸣器输出 */
    DL_GPIO_initDigitalOutput(IOMUX_PINCM13);
    DL_GPIO_enableOutput(GPIOB, DL_GPIO_PIN_1);

    /* 初始化完成后立即拉低，确保蜂鸣器和 LED 上电不动作 */
    DL_GPIO_clearPins(GPIOB, DL_GPIO_PIN_0 | DL_GPIO_PIN_1);
}

/******************************************************************
 * 函 数 名 称：Buzzer_On / Buzzer_Off
 * 函 数 说 明：蜂鸣器开关（PB1）
******************************************************************/
void Buzzer_On(void)
{
    DL_GPIO_setPins(GPIOB, DL_GPIO_PIN_1);
}

void Buzzer_Off(void)
{
    DL_GPIO_clearPins(GPIOB, DL_GPIO_PIN_1);
}

/******************************************************************
 * 函 数 名 称：Buzzer_Beep
 * 函 数 说 明：蜂鸣器响指定毫秒后关闭
******************************************************************/
void Buzzer_Beep(uint32_t duration_ms)
{
    /* 无源蜂鸣器：2kHz 方波（周期 500us） */
    uint32_t cycles = duration_ms * 4;  /* 1ms = 2 周期 = 4 次翻转 */
    uint32_t i;
    for (i = 0; i < cycles; i++)
    {
        DL_GPIO_setPins(GPIOB, DL_GPIO_PIN_1);
        delay_us(250);
        DL_GPIO_clearPins(GPIOB, DL_GPIO_PIN_1);
        delay_us(250);
    }
    Buzzer_Off();
}

/******************************************************************
 * 函 数 名 称：LED_On / LED_Off
 * 函 数 说 明：LED 开关（PB0）
******************************************************************/
void LED_On(void)
{
    DL_GPIO_setPins(GPIOB, DL_GPIO_PIN_0);
}

void LED_Off(void)
{
    DL_GPIO_clearPins(GPIOB, DL_GPIO_PIN_0);
}

/******************************************************************
 * 函 数 名 称：Signal_Point
 * 函 数 说 明：经过路径点时的声光提示
 *              蜂鸣器短响 200ms + LED 闪一次
 * 函 数 形 参：point_name 路径点名称 ('A'/'B'/'C'/'D')
******************************************************************/
void Signal_Point(char point_name)
{
    (void)point_name;  /* 预留，可用于不同点不同提示模式 */
    LED_On();
    Buzzer_Beep(200);
    LED_Off();
}
