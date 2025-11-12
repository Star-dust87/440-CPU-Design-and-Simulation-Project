import sys
import subprocess
from pathlib import Path

class TestSuite:
    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        
    def run_test(self, test_name, hex_file, expected_results):
        print(f"\n{'='*60}")
        print(f"Running Test: {test_name}")
        print(f"{'='*60}")
        
        try:
            result = subprocess.run(
                ['python3', 'riscv_cpu.py', hex_file],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            output = result.stdout
            
            all_passed = True
            for key, expected_value in expected_results.items():
                if key.startswith('x'):  
                    reg_num = key[1:]  
                    reg_pattern_lower = f"x {reg_num}=0x{expected_value:08x}"
                    reg_pattern_upper = f"x {reg_num}=0x{expected_value:08X}"
                    if reg_pattern_lower in output or reg_pattern_upper in output:
                        print(f"✓ {key} = 0x{expected_value:08x}")
                    else:
                        print(f"✗ {key} expected 0x{expected_value:08x}, check output format")
                        all_passed = False
                elif key == 'cycles':
                    if f"Cycles: {expected_value}" in output:
                        print(f"✓ Cycles = {expected_value}")
                    else:
                        print(f"✗ Cycles expected {expected_value}")
                        all_passed = False
                elif key.startswith('mem'):  
                    addr = int(key[3:], 16)
                    mem_pattern = f"0x{addr:08x}: 0x{expected_value:08x}"
                    if mem_pattern in output:
                        print(f"✓ Memory[0x{addr:08x}] = 0x{expected_value:08x}")
                    else:
                        print(f"✗ Memory[0x{addr:08x}] expected 0x{expected_value:08x}")
                        all_passed = False
            
            if all_passed:
                print(f"\n✓ Test '{test_name}' PASSED")
                self.tests_passed += 1
            else:
                print(f"\n✗ Test '{test_name}' FAILED")
                self.tests_failed += 1
                
        except subprocess.TimeoutExpired:
            print(f"✗ Test '{test_name}' TIMED OUT")
            self.tests_failed += 1
        except Exception as e:
            print(f"✗ Test '{test_name}' ERROR: {e}")
            self.tests_failed += 1
    
    def print_summary(self):
        total = self.tests_passed + self.tests_failed
        print(f"\n{'='*60}")
        print(f"TEST SUMMARY")
        print(f"{'='*60}")
        print(f"Total Tests:  {total}")
        print(f"Passed:       {self.tests_passed} ({100*self.tests_passed/total:.1f}%)")
        print(f"Failed:       {self.tests_failed}")
        print(f"{'='*60}\n")

def main():
    
    suite = TestSuite()
    
    print("RISC-V CPU Test Suite")
    print("="*60)
   
    suite.run_test(
        "Basic Functionality",
        "test_base.hex",
        {
            'x1': 0x00000005,
            'x2': 0x0000000A,
            'x3': 0x0000000F,
            'x4': 0x0000000F,
            'x5': 0x00010000,
            'x6': 0x00000002,
            'cycles': 9,
            'mem00010000': 0x0000000F
        }
    )
    
    suite.print_summary()
    
    return 0 if suite.tests_failed == 0 else 1

if __name__ == '__main__':
    sys.exit(main())
