#include "stm32f10x.h"                  // Device header
#include <stdio.h>
#include <stdarg.h>


uint8_t Serial_RxPacket[11];
uint8_t Serial_RxFlag;

void Serial_Init(void)
{
	RCC_APB2PeriphClockCmd(RCC_APB2Periph_USART1,ENABLE);
	RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOA,ENABLE);
	
	GPIO_InitTypeDef GPIO_InitStructure;
	GPIO_InitStructure.GPIO_Mode = GPIO_Mode_AF_PP;
	GPIO_InitStructure.GPIO_Pin = GPIO_Pin_9;
	GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
	GPIO_Init(GPIOA,&GPIO_InitStructure);
	
	GPIO_InitStructure.GPIO_Mode = GPIO_Mode_IPU;
	GPIO_InitStructure.GPIO_Pin = GPIO_Pin_10;
	GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
	GPIO_Init(GPIOA,&GPIO_InitStructure);
	
	USART_InitTypeDef USART_InitStructure;
	USART_InitStructure.USART_BaudRate = 9600;
	USART_InitStructure.USART_HardwareFlowControl  = USART_HardwareFlowControl_None;
	USART_InitStructure.USART_Mode = USART_Mode_Tx |USART_Mode_Rx;
	USART_InitStructure.USART_Parity = USART_Parity_No;
	USART_InitStructure.USART_StopBits = USART_StopBits_1;
	USART_InitStructure.USART_WordLength = USART_WordLength_8b;
	USART_Init (USART1 ,&USART_InitStructure);
	
	USART_ITConfig (USART1,USART_IT_RXNE,ENABLE);
	
	NVIC_PriorityGroupConfig (NVIC_PriorityGroup_2) ;
	NVIC_InitTypeDef NVIC_InitStructure;
	NVIC_InitStructure.NVIC_IRQChannel = USART1_IRQn;
	NVIC_InitStructure.NVIC_IRQChannelCmd  = ENABLE ;
	NVIC_InitStructure.NVIC_IRQChannelPreemptionPriority  = 1;
	NVIC_InitStructure.NVIC_IRQChannelSubPriority = 1;
	NVIC_Init(&NVIC_InitStructure );
	
	USART_Cmd(USART1 ,ENABLE);
}




  
uint8_t Serial_GetRxFlag(void)
{
	if (Serial_RxFlag == 1)			//如果标志位为1
	{
		Serial_RxFlag = 0;
		return 1;					//则返回1，并自动清零标志位
	}
	return 0;						//如果标志位为0，则返回0
}


void USART1_IRQHandler(void)
{
	static uint8_t RxState = 0;		//定义表示当前状态机状态的静态变量
	if (USART_GetITStatus(USART1, USART_IT_RXNE) == SET)		//判断是否是USART1的接收事件触发的中断
	{
		uint8_t RxData = USART_ReceiveData(USART1);				//读取数据寄存器，存放在接收的数据变量
		
		
		if (RxState == 0)
		{
			if (RxData == 0x55)			//如果数据确实是包头
			{
				Serial_RxPacket[0] = RxData;
				RxState = 1;		
			}
		}
		//接收数据包
		else if (RxState == 1)
		{
			if(RxData == 0x53)
			{
				Serial_RxPacket[1] = RxData ;
				RxState = 2 ;
			}
		}
		else  //RxState >=2 or<11
		{
		    Serial_RxPacket[RxState] = RxData ;
			RxState++ ;
			if(RxState >=11)
			{
				RxState = 0;
			}
		}
		USART_ClearITPendingBit(USART1, USART_IT_RXNE);		//清除标志位
	}
}
