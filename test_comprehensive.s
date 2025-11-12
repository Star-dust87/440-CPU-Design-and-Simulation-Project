.section .text
.globl _start
_start:
    # Logical operations
    addi x1, x0, 0xFF      # x1 = 0xFF
    addi x2, x0, 0xF0      # x2 = 0xF0
    and x3, x1, x2         # x3 = 0xF0
    or x4, x1, x2          # x4 = 0xFF
    xor x5, x1, x2         # x5 = 0x0F
    
    # Shift operations
    addi x6, x0, 8         # x6 = 8
    addi x7, x0, 2         # x7 = 2
    sll x8, x6, x7         # x8 = 32 (8 << 2)
    srl x9, x6, x7         # x9 = 2  (8 >> 2)
    
    # Arithmetic with immediates
    addi x10, x0, -1       # x10 = -1 (0xFFFFFFFF)
    addi x11, x10, 1       # x11 = 0
    
    # Branch not equal
    bne x11, x0, skip1
    addi x12, x0, 99       # This should execute
skip1:
    
    # LUI and AUIPC
    lui x13, 0x12345       # x13 = 0x12345000
    auipc x14, 0x100       # x14 = PC + 0x100000
    
    # JAL with link
    jal x15, target
    addi x16, x0, 1        # Should be skipped
target:
    addi x17, x0, 42       # x17 = 42
    
    # JALR test
    addi x18, x0, 0x6C     # Address of halt (assuming)
    jalr x19, x18, 0       # Jump to halt, save return address
    
halt:
    jal x0, 0              # Infinite loop
