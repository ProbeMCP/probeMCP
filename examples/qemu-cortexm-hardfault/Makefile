BUILD_DIR := build
ELF := $(BUILD_DIR)/hardfault.elf

CC ?= arm-none-eabi-gcc
CFLAGS := -mcpu=cortex-m3 -mthumb -ffreestanding -fdata-sections -ffunction-sections -g -O0 -Wall -Wextra
LDFLAGS := -nostdlib -Wl,--gc-sections -T linker.ld

.PHONY: all clean

all: $(ELF)

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

$(ELF): startup.s main.c linker.ld | $(BUILD_DIR)
	$(CC) $(CFLAGS) startup.s main.c $(LDFLAGS) -o $@

clean:
	rm -rf $(BUILD_DIR)
