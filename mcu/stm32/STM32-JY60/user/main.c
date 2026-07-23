#include "stm32f10x.h"                  // Device header
#include "Delay.h"
#include "OLED.h"
#include "serial.h"



uint16_t Roll,Pitch,Yaw;

int main(void)
{
	OLED_Init ();
	Serial_Init();

	
    while (1)
	{
	


            int16_t roll_raw  = (int16_t)( (Serial_RxPacket[3] << 8) | Serial_RxPacket[2] );
            int16_t pitch_raw = (int16_t)( (Serial_RxPacket[5] << 8) | Serial_RxPacket[4] );
            int16_t yaw_raw   = (int16_t)( (Serial_RxPacket[7] << 8) | Serial_RxPacket[6] );

         
            Roll  = roll_raw  / 100.0f;
            Pitch = pitch_raw / 100.0f;
            Yaw   = yaw_raw   / 100.0f;

            
            OLED_ShowSignedNum(1, 1, Roll,   5);  
            OLED_ShowSignedNum(2, 1, Pitch,  5);
            OLED_ShowSignedNum(3, 1, Yaw,    5);
    }
}
