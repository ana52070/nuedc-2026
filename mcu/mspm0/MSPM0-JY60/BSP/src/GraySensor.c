#include "GraySensor.h"
#include "ti_msp_dl_config.h"

/******************************************************************
 * 函 数 名 称：GraySensor_Init
 * 函 数 说 明：灰度传感器初始化
 *              配置 PB4-PB11 为数字输入 + 上拉
 *              PB4 → IOMUX_PINCM17 (GPIOB_DIO04)
 *              PB5 → IOMUX_PINCM18 (GPIOB_DIO05)
 *              PB6 → IOMUX_PINCM23 (GPIOB_DIO06)
 *              PB7 → IOMUX_PINCM24 (GPIOB_DIO07)
 *              PB8 → IOMUX_PINCM25 (GPIOB_DIO08)
 *              PB9 → IOMUX_PINCM26 (GPIOB_DIO09)
 *              PB10→ IOMUX_PINCM27 (GPIOB_DIO10)
 *              PB11→ IOMUX_PINCM28 (GPIOB_DIO11)
******************************************************************/
void GraySensor_Init(void)
{
    /* 配置 PB4-PB11 为上拉输入
     * RYDZ 灰度模块：白=低电平, 黑=高电平(上拉)
     */
    DL_GPIO_initDigitalInputFeatures(IOMUX_PINCM17,
        DL_GPIO_INVERSION_DISABLE, DL_GPIO_RESISTOR_PULL_UP,
        DL_GPIO_HYSTERESIS_DISABLE, DL_GPIO_WAKEUP_DISABLE);
    DL_GPIO_initDigitalInputFeatures(IOMUX_PINCM18,
        DL_GPIO_INVERSION_DISABLE, DL_GPIO_RESISTOR_PULL_UP,
        DL_GPIO_HYSTERESIS_DISABLE, DL_GPIO_WAKEUP_DISABLE);
    DL_GPIO_initDigitalInputFeatures(IOMUX_PINCM23,
        DL_GPIO_INVERSION_DISABLE, DL_GPIO_RESISTOR_PULL_UP,
        DL_GPIO_HYSTERESIS_DISABLE, DL_GPIO_WAKEUP_DISABLE);
    DL_GPIO_initDigitalInputFeatures(IOMUX_PINCM24,
        DL_GPIO_INVERSION_DISABLE, DL_GPIO_RESISTOR_PULL_UP,
        DL_GPIO_HYSTERESIS_DISABLE, DL_GPIO_WAKEUP_DISABLE);
    DL_GPIO_initDigitalInputFeatures(IOMUX_PINCM25,
        DL_GPIO_INVERSION_DISABLE, DL_GPIO_RESISTOR_PULL_UP,
        DL_GPIO_HYSTERESIS_DISABLE, DL_GPIO_WAKEUP_DISABLE);
    DL_GPIO_initDigitalInputFeatures(IOMUX_PINCM26,
        DL_GPIO_INVERSION_DISABLE, DL_GPIO_RESISTOR_PULL_UP,
        DL_GPIO_HYSTERESIS_DISABLE, DL_GPIO_WAKEUP_DISABLE);
    DL_GPIO_initDigitalInputFeatures(IOMUX_PINCM27,
        DL_GPIO_INVERSION_DISABLE, DL_GPIO_RESISTOR_PULL_UP,
        DL_GPIO_HYSTERESIS_DISABLE, DL_GPIO_WAKEUP_DISABLE);
    DL_GPIO_initDigitalInputFeatures(IOMUX_PINCM28,
        DL_GPIO_INVERSION_DISABLE, DL_GPIO_RESISTOR_PULL_UP,
        DL_GPIO_HYSTERESIS_DISABLE, DL_GPIO_WAKEUP_DISABLE);
}

/******************************************************************
 * 函 数 名 称：GraySensor_Read
 * 函 数 说 明：一次性读取 8 路灰度传感器
 * 函 数 返 回：uint8_t，bit0=OUT1(PB4) ... bit7=OUT8(PB11)，1=黑线
******************************************************************/
uint8_t GraySensor_Read(void)
{
    uint32_t raw = DL_GPIO_readPins(GPIOB, GRAYSENSOR_PIN_MASK);
    /* RYDZ 模块输出反相：白=高电平, 黑=低电平，取反后 bit=1 表示黑线 */
    return (uint8_t)(((raw >> GRAYSENSOR_PIN_SHIFT) & 0xFF) ^ 0xFF);
}

/******************************************************************
 * 函 数 名 称：GraySensor_GetPosition
 * 函 数 说 明：计算黑线在传感器阵列中的位置（加权平均）
 * 函 数 返 回：0 ~ 7000，3500 表示线在正中间
 *              返回 0xFFFF 表示未检测到黑线
******************************************************************/
uint16_t GraySensor_GetPosition(void)
{
    uint8_t  data = GraySensor_Read();
    uint32_t sum_weighted = 0;
    uint32_t sum_bits     = 0;
    uint8_t  i;

    if (data == 0)
    {
        return 0xFFFF;  /* 未检测到黑线 */
    }

    for (i = 0; i < 8; i++)
    {
        if (data & (1 << i))
        {
            sum_weighted += (uint32_t)i * GRAYSENSOR_WEIGHT_BASE;
            sum_bits++;
        }
    }

    if (sum_bits == 0)
    {
        return 0xFFFF;
    }

    return (uint16_t)(sum_weighted / sum_bits);
}
