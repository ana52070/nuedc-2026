  #ifndef __JY60_H
  #define __JY60_H

  #include <stdint.h>

  /* 接收数据包缓冲区，11字节（0x55 + 0x53 + 9字节数据） */
  extern volatile uint8_t Serial_RxPacket[11];

  /* 接收完成标志位（由 ISR 置 1，GetRxFlag 读取后自动清零） */
  extern volatile uint8_t Serial_RxFlag;

  void Serial_Init(void);
  uint8_t Serial_GetRxFlag(void);

  #endif