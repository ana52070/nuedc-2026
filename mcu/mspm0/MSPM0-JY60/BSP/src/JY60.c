  #include "JY60.h"
  #include "ti_msp_dl_config.h"
  #include "Board.h"

  /* ============ 全局变量定义 ============ */
  volatile uint8_t Serial_RxPacket[11];
  volatile uint8_t Serial_RxFlag;

  /* ============ Serial_Init ============
   * 使能 UART0 接收中断并开启 NVIC
   * 注意：UART 硬件本身 (GPIO/波特率) 已被 SYSCFG_DL_init() 配置好
   * ==================================== */
  void Serial_Init(void)
  {
      /* 使能 UART0 接收中断 */
      DL_UART_Main_enableInterrupt(UART_0_INST, DL_UART_MAIN_INTERRUPT_RX);

      /* 使能 NVIC 中的 UART0 中断线 */
      NVIC_EnableIRQ(UART_0_INST_INT_IRQN);
  }

  /* ============ Serial_GetRxFlag ============
   * 检测是否收到完整的一包数据
   * 返回 1：有新数据；返回 0：无新数据
   * 读取后自动清零标志位
   * ======================================== */
  uint8_t Serial_GetRxFlag(void)
  {
      if (Serial_RxFlag == 1)
      {
          Serial_RxFlag = 0;
          return 1;
      }
      return 0;
  }

  /* ============ UART0 中断服务函数 ============
   * 覆盖 DriverLib 中的弱定义 (weak) 默认 ISR
   * 状态机解析 JY60 串口陀螺仪协议：
   *   帧头: 0x55 0x53
   *   帧长: 11 字节 (包头 2 + 数据 9)
   * ========================================== */
  void UART_0_INST_IRQHandler(void)
  {
      static uint8_t RxState = 0;

      switch (DL_UART_Main_getPendingInterrupt(UART_0_INST))
      {
      case DL_UART_MAIN_IIDX_RX:
      {
          uint8_t RxData = DL_UART_Main_receiveData(UART_0_INST);

          if (RxState == 0)
          {
              if (RxData == 0x55)
              {
                  Serial_RxPacket[0] = RxData;
                  RxState = 1;
              }
          }
          else if (RxState == 1)
          {
              if (RxData == 0x53)
              {
                  Serial_RxPacket[1] = RxData;
                  RxState = 2;
              }
              else
              {
                  RxState = 0;   /* 第二字节不匹配，回退等下一帧 */
              }
          }
          else   /* RxState 2 ~ 10 */
          {
              Serial_RxPacket[RxState] = RxData;
              RxState++;

              if (RxState >= 11)
              {
                  RxState = 0;
                  Serial_RxFlag = 1;   /* 完整一帧接收完成 */
              }
          }
          break;
      }

      default:
          break;
      }
  }