#ifndef __JY60_H
#define __JY60_H

void jy61p_ReceiveData(uint8_t RxData);
extern uint16_t Roll,Pitch,Yaw;
uint16_t u16_to_angle(uint16_t data);
uint16_t angle_to_u16(uint16_t angle);


#endif

