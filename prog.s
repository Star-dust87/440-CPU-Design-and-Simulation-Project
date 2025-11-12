.section .text
.globl _start
_start:
    addi x1, x0, 5          
    addi x2, x0, 10         
    add x3, x1, x2          
    sub x4, x2, x1          
    lui x5, 0x00010         
    sw x3, 0(x5)            
    lw x4, 0(x5)            
    beq x3, x4, label1      
    addi x6, x0, 1          
label1:
    addi x6, x0, 2          
    jal x0, 0               
