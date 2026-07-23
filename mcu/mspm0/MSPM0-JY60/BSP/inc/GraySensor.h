#ifndef _BSP_GRAYSENSOR_H
#define _BSP_GRAYSENSOR_H

#include <stdint.h>

/* 8路灰度传感器：OUT1(最左) ~ OUT8(最右)，映射到 PB4 ~ PB11
 * bit0 = OUT1, bit1 = OUT2, ..., bit7 = OUT8
 * 1 = 检测到黑线，0 = 白色地面
 */
#define GRAYSENSOR_PIN_MASK    (0x0FF0u)   /* PB4-PB11 */
#define GRAYSENSOR_PIN_SHIFT   4

/* 传感器编号 0~7 对应的权重 (用于计算线位置) */
#define GRAYSENSOR_WEIGHT_BASE 1000

void    GraySensor_Init(void);
uint8_t GraySensor_Read(void);
uint16_t GraySensor_GetPosition(void);

#endif /* _BSP_GRAYSENSOR_H */
