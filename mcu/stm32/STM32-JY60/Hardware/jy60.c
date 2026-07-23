#include "stm32f10x.h"                  // Device header
#include "serial.h"


static uint8_t RxBuffer[11];/*接收数据数组*/
static volatile uint8_t RxState = 0;/*接收状态标志位*/
static uint8_t RxIndex = 0;/*接受数组索引*/
uint16_t Roll,Pitch,Yaw;/*角度信息，如果只需要整数可以改为整数类型*/


/**
 * @brief       数据包处理函数
 * @param       串口接收的数据RxData
 * @retval      无
 */
void jy61p_ReceiveData(uint8_t RxData)
{
	uint8_t i,sum=0;
	
	if (RxState == 0)	//等待包头
	{
		if (RxData == 0x55)	//收到包头
		{
			RxBuffer[RxIndex] = RxData;
			RxState = 1;
			RxIndex = 1; //进入下一状态
		}
	}
	
	else if (RxState == 1)
	{
		if (RxData == 0x53)	/*判断数据内容，修改这里可以改变要读的数据内容，0x53为角度输出*/
		{
			RxBuffer[RxIndex] = RxData;
			RxState = 2;
			RxIndex = 2; //进入下一状态
		}
	}
	
	else if (RxState == 2)	//接收数据
	{
		RxBuffer[RxIndex++] = RxData;
		if(RxIndex == 11)	//接收完成
		{
			for(i=0;i<10;i++)
			{
				sum = sum + RxBuffer[i]; //计算校验和
			}
			if(sum == RxBuffer[10])		//校验成功
			{
				/*计算数据，根据数据内容选择对应的计算公式*/
				Roll =  (uint16_t)RxBuffer[3] << 8 | (uint16_t)RxBuffer[2];
				Pitch = (uint16_t)RxBuffer[5] << 8 | (uint16_t)RxBuffer[4];
				Yaw =   (uint16_t)RxBuffer[7] << 8 | (uint16_t)RxBuffer[6];
			}
			RxState = 0;
			RxIndex = 0; //读取完成，回到最初状态，等待包头
		}
	}
}

/**
 * @brief       把原始16位数据转换为角度
 * @param       原始16位数据
 * @retval      计算的角度值
 */
uint16_t u16_to_angle(uint16_t data)
{
    uint16_t angle = 0;
    angle = data * 180 / 32768;     //这里一定要先乘再除，否则整数相除可能导致数据丢失
    return angle;
}
    
/**
 * @brief       把角度值转换为16位
 * @param       角度
 * @retval      16位数据
 */
uint16_t angle_to_u16(uint16_t angle)
{
    uint16_t data = 0;
    data = angle * 32768 / 180;     //这里一定要先乘再除，否则整数相除可能导致数据丢失
    return data;
}