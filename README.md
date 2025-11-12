# RISC-V RV32I Single-Cycle CPU Simulator

A complete implementation of a 32-bit RISC-V processor in Python, implementing the RV32I 
instruction set architecture.

## Project Overview

This project implements a single-cycle RISC-V CPU that executes a subset of the RV32I ISA. 
The implementation includes all major components of a CPU: ALU, Register File, Control Unit, 
Memory, and complete instruction decode logic.

## Features

### Implemented Components

1. **Arithmetic Logic Unit (ALU)**
   - Supports 10 operations: ADD, SUB, SLL, SLT, SLTU, XOR, SRL, SRA, OR, AND
   - Full 32-bit signed and unsigned arithmetic
   - Proper shift operations with 5-bit shift amounts

2. **Register File**
   - 32 general-purpose registers (x0-x31)
   - x0 hardwired to zero
   - 32-bit word size
   - Simultaneous read of two registers
   - Single-cycle write capability

3. **Memory System**
   - Unified instruction and data memory
   - 128KB default size (configurable)
   - Little-endian byte ordering
   - Word-aligned access
   - Support for loading programs from .hex files

4. **Control Unit**
   - Combinational logic for generating control signals
   - Supports all implemented instruction types
   - Generates signals for: RegWrite, MemRead, MemWrite, MemToReg, ALUSrc, Branch, Jump

5. **Instruction Decoder**
   - Complete decoding of RV32I instruction formats (R, I, S, B, U, J)
   - Proper immediate extraction and sign extension
   - Funct3 and Funct7 field extraction

#### Arithmetic (5 instructions)
- `ADD rd, rs1, rs2` - Add
- `SUB rd, rs1, rs2` - Subtract
- `ADDI rd, rs1, imm` - Add immediate

#### Logical (6 instructions)
- `AND rd, rs1, rs2` - Bitwise AND
- `OR rd, rs1, rs2` - Bitwise OR
- `XOR rd, rs1, rs2` - Bitwise XOR
- `ANDI rd, rs1, imm` - AND immediate
- `ORI rd, rs1, imm` - OR immediate
- `XORI rd, rs1, imm` - XOR immediate

#### Shift (6 instructions)
- `SLL rd, rs1, rs2` - Shift left logical
- `SRL rd, rs1, rs2` - Shift right logical
- `SRA rd, rs1, rs2` - Shift right arithmetic
- `SLLI rd, rs1, imm` - Shift left logical immediate
- `SRLI rd, rs1, imm` - Shift right logical immediate
- `SRAI rd, rs1, imm` - Shift right arithmetic immediate

#### Memory (2 instructions)
- `LW rd, offset(rs1)` - Load word
- `SW rs2, offset(rs1)` - Store word

#### Branch (6 instructions)
- `BEQ rs1, rs2, offset` - Branch if equal
- `BNE rs1, rs2, offset` - Branch if not equal
- `BLT rs1, rs2, offset` - Branch if less than (signed)
- `BGE rs1, rs2, offset` - Branch if greater or equal (signed)
- `BLTU rs1, rs2, offset` - Branch if less than (unsigned)
- `BGEU rs1, rs2, offset` - Branch if greater or equal (unsigned)

#### Jump (2 instructions)
- `JAL rd, offset` - Jump and link
- `JALR rd, rs1, offset` - Jump and link register

#### Upper Immediate (2 instructions)
- `LUI rd, imm` - Load upper immediate
- `AUIPC rd, imm` - Add upper immediate to PC

## Architecture

### CPU Block Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         RISC-V CPU                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌────┐      ┌──────────┐      ┌─────────────┐            │
│  │ PC │─────→│ Instr    │─────→│ Instruction │            │
│  └────┘      │ Memory   │      │   Decoder   │            │
│    │         └──────────┘      └─────────────┘            │
│    │                                  │                    │
│    │         ┌──────────┐             │                    │
│    └────────→│ Control  │←────────────┘                    │
│              │   Unit   │                                  │
│              └──────────┘                                  │
│                   │                                        │
│                   │ (control signals)                      │
│                   ↓                                        │
│  ┌─────────────────────────────────────────┐              │
│  │          Register File (x0-x31)         │              │
│  │  ┌──────┐    ┌──────┐     ┌──────┐    │              │
│  │  │ rs1  │    │ rs2  │     │  rd  │    │              │
│  │  └──┬───┘    └───┬──┘     └───┬──┘    │              │
│  └─────┼───────────┼─────────────┼────────┘              │
│        │           │             │                        │
│        ↓           ↓             ↑                        │
│     ┌──────────────────┐         │                        │
│     │   MUX (ALUSrc)   │         │                        │
│     └────────┬─────────┘         │                        │
│              ↓                   │                        │
│        ┌──────────┐              │                        │
│        │   ALU    │──────────────┤                        │
│        └──────────┘              │                        │
│              │                   │                        │
│              ↓                   │                        │
│        ┌──────────┐              │                        │
│        │   Data   │              │                        │
│        │  Memory  │──────────────┘                        │
│        └──────────┘                                       │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### Datapath Description

The single-cycle datapath executes each instruction in one clock cycle through five stages:

1. **Instruction Fetch (IF)**
   - PC provides address to instruction memory
   - 32-bit instruction is fetched

2. **Instruction Decode (ID)**
   - Instruction is decoded into opcode, registers, immediates
   - Control unit generates control signals
   - Register file provides operand data

3. **Execute (EX)**
   - ALU performs operation based on ALUOp control signal
   - Branch conditions evaluated
   - Target addresses calculated for jumps/branches

4. **Memory Access (MEM)**
   - Load: Read data from memory
   - Store: Write data to memory
   - Other instructions: Pass through

5. **Write Back (WB)**
   - Result written to destination register (if RegWrite asserted)
   - PC updated to next instruction (or branch/jump target)

### Control Signals

| Signal | Purpose |
|--------|---------|
| RegWrite | Enable writing to register file |
| MemRead | Enable reading from data memory |
| MemWrite | Enable writing to data memory |
| MemToReg | Select between ALU result and memory data |
| ALUSrc | Select between register and immediate for ALU |
| Branch | Instruction is a branch |
| Jump | Instruction is a jump (JAL/JALR) |

## Usage

### Running a Program

```bash
python3 riscv_cpu.py <prog.hex> [--debug]
```

Options:
- `<prog.hex>`: Path to the hex file containing the program
- `--debug`: Enable debug output (shows each instruction execution)

### Example

```bash
# Run the test program
python3 riscv_cpu.py test_base.hex

# Run with debug output
python3 riscv_cpu.py test_base.hex --debug
```

### Program Format

Programs must be in `.hex` format with the following specifications:
- One 32-bit instruction per line
- 8 hexadecimal digits per instruction
- Little-endian encoding
- No `0x` prefix
- Uppercase or lowercase accepted

Example:
```
00500093
00A00113
002081B3
```

## Test Results

### Test Program: prog.hex

**Description:** Basic functionality test covering arithmetic, memory operations, branching, and control flow.

**Instructions Executed:** 9

**Expected Results:**
- x1 = 5
- x2 = 10
- x3 = 15 (5 + 10)
- x4 = 15 (loaded from memory)
- x5 = 0x00010000
- x6 = 2 (branch taken, skipped x6=1)
- Memory[0x10000] = 15

**Actual Results:** ✓ All tests passed

**Output:**
```
Program loaded from prog.hex

=== Starting CPU Execution ===

Halt detected at PC=0x00000028 (infinite loop)

Execution complete:
  Cycles: 9
  Instructions: 9
  Final PC: 0x00000028

CPU STATE DUMP
PC: 0x00000028
Cycles: 9
Instructions: 9

Register File:
x 0=0x00000000  x 1=0x00000005  x 2=0x0000000a  x 3=0x0000000f  
x 4=0x0000000f  x 5=0x00010000  x 6=0x00000002  x 7=0x00000000  
...

Memory Dump [0x00010000 - 0x0001000f]:
  0x00010000: 0x0000000f
```

## Project Structure

```
.
├── riscv_cpu.py           # Main CPU implementation
├── riscv_cpu_pipelined.py # Pipeline implementation
├── test_base.hex          # Provided test program
├── test_base.s            # Assembly source for test program
├── test_comprehensive.s   # Extended test program
├── README.md              # This file
└── design_doc.md          # Detailed design documentation
```

## Design Decisions

### Single-Cycle Implementation

The processor executes each instruction in a single clock cycle. While this is simpler to implement and understand, it has the following characteristics:


### Memory Organization

- **Unified Memory**: Single memory space for instructions and data simplifies the design
- **Word-Aligned Access**: All memory accesses must be word-aligned (4-byte boundaries)
- **Data Memory Base**: Test programs assume data memory starts at 0x00010000

### Register File

- x0 is hardwired to 0 (writes are ignored)
- All registers are 32-bits
- Supports 2 simultaneous reads and 1 write per cycle


## AI Usage Log

Claude 3.5 Sonnet (Anthropic)
- Version: Claude Sonnet 4.5

This project was developed with AI assistance for:

1. **Documentation**: AI helped structure the README and design documentation for clarity and completeness.

   Prompt: Help create README.md and design document.md

2. **Debugging**: AI helped identify and fix issues with:
   - Sign extension in immediate values
   - Branch offset calculation
   - Memory addressing in little-endian format
  
     Prompt: Review my code

3. **Standard Program File**: AI helped create prog.hex
   -Binary machine code

   Prompt: Create prog.hex

All code was reviewed, tested, and verified by the student. 
The core algorithm design and implementation decisions were made by the student with AI 
providing suggestions and catching potential errors.
