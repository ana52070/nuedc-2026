#ifndef _BSP_BUZZER_H
#define _BSP_BUZZER_H

#include <stdint.h>

/* 蜂鸣器: PB1, LED: PB0 */

void Buzzer_LED_Init(void);
void Buzzer_On(void);
void Buzzer_Off(void);
void Buzzer_Beep(uint32_t duration_ms);
void LED_On(void);
void LED_Off(void);

/* 经过路径点 A/B/C/D 时声光提示 */
void Signal_Point(char point_name);

#endif /* _BSP_BUZZER_H */
