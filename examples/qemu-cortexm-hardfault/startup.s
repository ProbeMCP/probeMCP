.syntax unified
.cpu cortex-m3
.thumb

.global Reset_Handler
.global HardFault_Handler
.extern main

.section .isr_vector, "a", %progbits
.word _estack
.word Reset_Handler
.word Default_Handler
.word HardFault_Handler
.word Default_Handler
.word Default_Handler
.word Default_Handler
.word 0
.word 0
.word 0
.word 0
.word Default_Handler
.word Default_Handler
.word 0
.word Default_Handler
.word Default_Handler

.section .text.Reset_Handler, "ax", %progbits
.thumb_func
Reset_Handler:
  bl main
  b .

.section .text.HardFault_Handler, "ax", %progbits
.thumb_func
HardFault_Handler:
  b .

.section .text.Default_Handler, "ax", %progbits
.thumb_func
Default_Handler:
  b .
