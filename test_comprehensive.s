.section .text
.globl _start
_start:
    addi x1, x0, 0xFF     
    addi x2, x0, 0xF0      
    and x3, x1, x2         
    or x4, x1, x2          
    xor x5, x1, x2         
    
    addi x6, x0, 8         
    addi x7, x0, 2         
    sll x8, x6, x7         
    srl x9, x6, x7        
    
    addi x10, x0, -1       
    addi x11, x10, 1       
    
    bne x11, x0, skip1
    addi x12, x0, 99       
skip1:
    
    lui x13, 0x12345       
    auipc x14, 0x100       
    
    jal x15, target
    addi x16, x0, 1        
target:
    addi x17, x0, 42       
    
    addi x18, x0, 0x6C     
    jalr x19, x18, 0       
    
halt:
    jal x0, 0              
