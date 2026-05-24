__attribute__((noreturn)) int main(void) {
  __asm volatile("udf #0");
  while (1) {
  }
}
