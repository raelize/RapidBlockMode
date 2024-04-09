#include <stdbool.h>
#include <stdio.h>
#include <string.h>

#include "esp_log.h"
#include "bootloader_init.h"
#include "bootloader_utility.h"
#include "bootloader_common.h"

#include "esp32/rom/gpio.h"
#include "esp_rom_gpio.h"
#include "esp_rom_uart.h"
#include "esp_rom_sys.h"
#include "bootloader_random.h"

#include "soc/hwcrypto_reg.h"
#include "soc/dport_access.h"
#include "soc/dport_reg.h"
#include "esp32/rom/aes.h"
#include "esp32/rom/sha.h"

#define AES128 0

void printhex(uint8_t *data) {
    for(int i = 0; i < 16; i++) {   
        esp_rom_printf("%02x", data[i]);
    }
    esp_rom_printf("\n");
}

void __attribute__((noreturn)) call_start_cpu0(void)
{
    // 1. Hardware initialization
    if (bootloader_init() != ESP_OK) {
        bootloader_reset();
    }

    /* raelize */
    esp_rom_printf("RapidBlockMode (press 'H' for help...)\n");

    uint8_t tkey[16] = { 0 };
    uint8_t tin[16] = { 0 };
    uint8_t tout[16] = { 0 };

    uint8_t input[16] = { 0 };
    
    uint8_t l,h;
    uint16_t iterations;    

    ets_aes_enable();

    uint8_t command;
    GPIO_OUTPUT_SET(26,0);

    while(1) {
        memset(tin, 0x00, sizeof(tin));
        memset(tout, 0x00, sizeof(tin));

        while(esp_rom_uart_rx_one_char(&command) != 0){};

        switch(command) {

            // set key
            case 'K':
                for(int i = 0; i < 16; i++) {
                    while(esp_rom_uart_rx_one_char(&tkey[i]) != 0){};
                }
                esp_rom_printf("OK\n");
                break;

            // averaged encryptions
            case 'L':
                
                while(esp_rom_uart_rx_one_char(&h) != 0){};
                while(esp_rom_uart_rx_one_char(&l) != 0){};

                iterations = ((uint16_t)h << 8) | l;

                /* get input */
                for(int i = 0; i < 16; i++) {
                    while(esp_rom_uart_rx_one_char(&tin[i]) != 0){};
                }

                /* set key */
                ets_aes_setkey_enc(tkey, AES128);

                for(int i= 0; i < iterations; i++) {
                    GPIO_OUTPUT_SET(26,1);
                    ets_aes_crypt(tin, tout);
                    GPIO_OUTPUT_SET(26,0);
                }

                /* print output */
                printhex(tout);
                break;

            // generate input with AES engine based of input
            case 'M':
            
                /* set key */
                ets_aes_setkey_enc(tkey, AES128);

                // iterations
                while(esp_rom_uart_rx_one_char(&h) != 0){};
                while(esp_rom_uart_rx_one_char(&l) != 0){};
                iterations = ((uint16_t)h << 8) | l;

                /* get input (seed) */
                for(int i = 0; i < 16; i++) {
                    while(esp_rom_uart_rx_one_char(&input[i]) != 0){};
                }

                /* as many encryptions as iterations */
                for(int i= 0; i < iterations; i++) {
            
                    /* attack here */
                    GPIO_OUTPUT_SET(26,1);
                    ets_aes_crypt(input, input);
                    GPIO_OUTPUT_SET(26,0);
                }

                /* print output */
                esp_rom_printf("OK\n");
                break;

            /* print help */
            case 'H':
                esp_rom_printf("Supported commands:\n");

                esp_rom_printf("- K: set key\n");
                esp_rom_printf("- L: encrypt data with key (multi avareged)\n");
                esp_rom_printf("- M: encrypt data with key (multi non-averaged)\n");
                esp_rom_printf("- H: print help\n");
                break;
            default:
                esp_rom_printf("ERROR: command not supported\n");
        }
    }

    while(1);
}
